import logging
import os
import tempfile
import time
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from app.config import settings

logger = logging.getLogger(__name__)

AUDIO_MIME_TYPES: dict[str, str] = {
    "mp3": "audio/mpeg",
    "m4a": "audio/mp4",
    "wav": "audio/wav",
    "webm": "audio/webm",
    "ogg": "audio/ogg",
}

# 15MB 이하는 인라인 바이트로 전송, 초과는 Gemini Files API 사용
INLINE_AUDIO_LIMIT_BYTES = 15 * 1024 * 1024
FILE_ACTIVE_TIMEOUT_SECONDS = 60
FILE_ACTIVE_POLL_INTERVAL_SECONDS = 2


class TranscriptSegment(BaseModel):
    """타임스탬프가 포함된 음성 전사 구간"""

    start_time: str = Field(..., description="시작 시각 (예: 00:00)")
    end_time: str = Field(..., description="종료 시각 (예: 01:30)")
    text: str = Field(..., description="전사된 한국어/영어 의학 강의 내용")


class AudioTranscriptOutput(BaseModel):
    """Gemini Audio 멀티모달 전사 결과 스키마"""

    segments: list[TranscriptSegment] = Field(
        default_factory=list,
        description="시간순으로 정리된 음성 전사 구간 목록",
    )


def get_audio_mime_type(ext: str) -> str:
    """확장자에 맞는 표준 오디오 MIME 타입 반환"""
    return AUDIO_MIME_TYPES.get(ext.lower(), "audio/mpeg")


def _get_gemini_client() -> genai.Client:
    """Gemini Audio 전사용 클라이언트 생성"""
    api_key = (settings.gemini_api_key or "").strip()
    if not api_key or "your_gemini_api_key" in api_key:
        raise ValueError(
            "음성 전사(Gemini Audio)를 위해 GEMINI_API_KEY가 필요합니다. "
            "backend/.env 또는 Render.com 환경변수에 GEMINI_API_KEY를 설정해 주세요."
        )
    return genai.Client(api_key=api_key)


def _segments_to_pages(segments: list[TranscriptSegment], max_pages: int, chunk_size: int = 1500) -> list[dict]:
    """타임스탬프 세그먼트 목록을 기존 문서 뷰어/요약 파이프라인 호환 page_contents로 변환"""
    pages: list[dict] = []
    current_lines: list[str] = []
    current_len = 0
    page_num = 1

    for seg in segments:
        cleaned_text = (seg.text or "").strip()
        if not cleaned_text:
            continue
        start = (seg.start_time or "00:00").strip()
        end = (seg.end_time or "").strip()
        time_tag = f"[{start} ~ {end}]" if end else f"[{start}]"
        line = f"{time_tag} {cleaned_text}"

        if current_lines and current_len + len(line) > chunk_size:
            pages.append({"page": page_num, "text": "\n".join(current_lines)})
            page_num += 1
            if page_num > max_pages:
                raise ValueError(f"음성 전사 최대 분량 제한({max_pages}구간)을 초과했습니다.")
            current_lines = []
            current_len = 0

        current_lines.append(line)
        current_len += len(line)

    if current_lines:
        pages.append({"page": page_num, "text": "\n".join(current_lines)})

    if not pages:
        pages.append({"page": 1, "text": ""})
    return pages


def _get_file_state_name(file_obj) -> str:
    """Gemini Files API 응답 객체에서 상태 문자열(ACTIVE/PROCESSING/FAILED 등)을 안전하게 추출"""
    state = getattr(file_obj, "state", None)
    if state is None:
        return ""
    name = getattr(state, "name", None)
    return str(name or state).upper()


def _wait_for_uploaded_file_active(client: genai.Client, uploaded_file, filename: str):
    """Gemini Files API 업로드 후 오디오 파일이 ACTIVE 상태가 될 때까지 대기"""
    file_name = getattr(uploaded_file, "name", None)
    state = _get_file_state_name(uploaded_file)
    logger.info(
        "[Audio STT] Gemini Files API 업로드 완료: filename=%s, remote_name=%s, initial_state=%s",
        filename,
        file_name,
        state or "UNKNOWN",
    )
    if not file_name or state in ("", "ACTIVE"):
        return uploaded_file

    deadline = time.monotonic() + FILE_ACTIVE_TIMEOUT_SECONDS
    current_file = uploaded_file
    while time.monotonic() < deadline:
        if state == "ACTIVE":
            return current_file
        if "FAIL" in state:
            raise ValueError(f"Gemini 오디오 파일 처리에 실패했습니다 (state={state}).")
        time.sleep(FILE_ACTIVE_POLL_INTERVAL_SECONDS)
        current_file = client.files.get(name=file_name)
        state = _get_file_state_name(current_file)
        logger.info(
            "[Audio STT] Gemini Files 상태 폴링: filename=%s, remote_name=%s, state=%s",
            filename,
            file_name,
            state,
        )

    if state != "ACTIVE":
        raise ValueError(f"Gemini 오디오 파일 준비 시간 초과 (state={state}). 잠시 후 다시 시도해 주세요.")
    return current_file


def transcribe_audio_bytes(file_bytes: bytes, filename: str) -> list[dict]:
    """
    Gemini Audio 멀티모달을 사용해 음성 파일 바이트를 전사하고
    타임스탬프 구간별 page_contents 목록을 반환한다.
    """
    started_at = time.monotonic()
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "mp3"
    mime_type = get_audio_mime_type(ext)
    size_mb = len(file_bytes) / (1024 * 1024)
    upload_mode = "inline" if len(file_bytes) <= INLINE_AUDIO_LIMIT_BYTES else "files_api"

    logger.info(
        "[Audio STT] 전사 시작: filename=%s, ext=%s, mime=%s, size=%.2fMB, mode=%s, model=%s",
        filename,
        ext,
        mime_type,
        size_mb,
        upload_mode,
        settings.gemini_stt_model,
    )

    client = _get_gemini_client()

    prompt = (
        "당신은 의과대학 강의 전문 속기사입니다. 첨부된 음성 파일의 내용을 빠짐없이 정확하게 전사하세요.\n"
        "[규칙]\n"
        "1. 한국어 설명과 영어 의학 전문용어(질환명, 해부학 용어, 약물명, 약어 등)를 원음에 맞게 정확히 표기하세요.\n"
        "2. 의미 단위 또는 약 1~2분 단위로 구간(segments)을 나누고, 각 구간의 start_time(MM:SS), end_time(MM:SS), text를 JSON으로 출력하세요.\n"
        "3. 요약하거나 생략하지 말고 실제 발화 내용을 충실하게 텍스트로 옮겨 적으세요."
    )

    uploaded_file = None
    tmp_path = None
    try:
        if upload_mode == "inline":
            audio_part = types.Part.from_bytes(data=file_bytes, mime_type=mime_type)
            contents = [prompt, audio_part]
        else:
            # 15MB 초과 오디오는 임시 파일로 저장 후 Gemini Files API를 통해 업로드
            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as tmp:
                tmp.write(file_bytes)
                tmp_path = tmp.name
            logger.info("[Audio STT] 임시 파일 생성 완료, Gemini Files API 업로드 시작: %s", tmp_path)
            uploaded_file = client.files.upload(
                file=tmp_path,
                config={"mime_type": mime_type},
            )
            uploaded_file = _wait_for_uploaded_file_active(client, uploaded_file, filename)
            contents = [prompt, uploaded_file]

        gen_started_at = time.monotonic()
        logger.info("[Audio STT] Gemini generate_content 호출 시작: filename=%s, model=%s", filename, settings.gemini_stt_model)
        response = client.models.generate_content(
            model=settings.gemini_stt_model,
            contents=contents,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=AudioTranscriptOutput,
                temperature=0.1,
            ),
        )
        gen_elapsed = time.monotonic() - gen_started_at
        raw_text = (response.text or "").strip()
        logger.info(
            "[Audio STT] Gemini generate_content 응답 수신: filename=%s, elapsed=%.2fs, response_chars=%d",
            filename,
            gen_elapsed,
            len(raw_text),
        )
        if not raw_text:
            raise ValueError("Gemini Audio 전사 응답이 비어 있습니다.")

        parsed = AudioTranscriptOutput.model_validate_json(raw_text)
        pages = _segments_to_pages(parsed.segments, max_pages=settings.max_document_pages)
        total_elapsed = time.monotonic() - started_at
        logger.info(
            "[Audio STT] 전사 완료: filename=%s, segments=%d, pages=%d, total_elapsed=%.2fs",
            filename,
            len(parsed.segments),
            len(pages),
            total_elapsed,
        )
        return pages
    except Exception:
        logger.exception(
            "[Audio STT] 전사 중 예외 발생: filename=%s, size=%.2fMB, mode=%s, elapsed=%.2fs",
            filename,
            size_mb,
            upload_mode,
            time.monotonic() - started_at,
        )
        raise
    finally:
        if uploaded_file is not None and getattr(uploaded_file, "name", None):
            try:
                client.files.delete(name=uploaded_file.name)
                logger.info("[Audio STT] Gemini 임시 업로드 오디오 파일 삭제 완료: %s", uploaded_file.name)
            except Exception:
                logger.warning("[Audio STT] Gemini 임시 업로드 오디오 파일 삭제 실패: %s", uploaded_file.name)
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                logger.warning("[Audio STT] 로컬 임시 오디오 파일 삭제 실패: %s", tmp_path)
