import logging
import os
import tempfile
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


def transcribe_audio_bytes(file_bytes: bytes, filename: str) -> list[dict]:
    """
    Gemini Audio 멀티모달을 사용해 음성 파일 바이트를 전사하고
    타임스탬프 구간별 page_contents 목록을 반환한다.
    """
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "mp3"
    mime_type = get_audio_mime_type(ext)
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
        if len(file_bytes) <= INLINE_AUDIO_LIMIT_BYTES:
            audio_part = types.Part.from_bytes(data=file_bytes, mime_type=mime_type)
            contents = [prompt, audio_part]
        else:
            # 15MB 초과 오디오는 임시 파일로 저장 후 Gemini Files API를 통해 업로드
            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as tmp:
                tmp.write(file_bytes)
                tmp_path = tmp.name
            uploaded_file = client.files.upload(
                file=tmp_path,
                config={"mime_type": mime_type},
            )
            contents = [prompt, uploaded_file]

        response = client.models.generate_content(
            model=settings.gemini_stt_model,
            contents=contents,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=AudioTranscriptOutput,
                temperature=0.1,
            ),
        )
        parsed = AudioTranscriptOutput.model_validate_json(response.text)
        return _segments_to_pages(parsed.segments, max_pages=settings.max_document_pages)
    finally:
        if uploaded_file is not None and getattr(uploaded_file, "name", None):
            try:
                client.files.delete(name=uploaded_file.name)
            except Exception:
                logger.warning("Gemini 임시 업로드 오디오 파일 삭제 실패: %s", uploaded_file.name)
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                logger.warning("로컬 임시 오디오 파일 삭제 실패: %s", tmp_path)
