import logging
import time
from typing import Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from starlette.concurrency import run_in_threadpool
from app.config import settings
from app.services.audio_service import get_audio_mime_type
from app.services.auth_service import require_auth
from app.services.document_parser import is_audio_extension, parse_document_bytes, validate_file_extension
from app.services.supabase_service import store

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/api/documents",
    tags=["documents"],
    dependencies=[Depends(require_auth)],
)


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    title: Optional[str] = Form(default=None),
    category: str = Form(default="일반의학"),
):
    """학습 자료(PDF, DOCX, PPTX, TXT, MD) 업로드 및 페이지별 텍스트 파싱"""
    req_started_at = time.monotonic()
    if not file.filename:
        raise HTTPException(status_code=400, detail="파일명이 비어 있습니다.")

    try:
        validated_ext = validate_file_extension(file.filename)
    except ValueError as exc:
        logger.warning("[Upload] 허용되지 않은 확장자 (%s): %s", file.filename, exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    is_audio = is_audio_extension(validated_ext)
    logger.info(
        "[Upload] 요청 수신: filename=%s, ext=%s, is_audio=%s, raw_content_type=%s",
        file.filename,
        validated_ext,
        is_audio,
        file.content_type,
    )

    max_bytes = settings.max_upload_mb * 1024 * 1024
    file_bytes = await file.read(max_bytes + 1)
    if not file_bytes:
        raise HTTPException(status_code=400, detail="빈 파일은 업로드할 수 없습니다.")
    if len(file_bytes) > max_bytes:
        logger.warning(
            "[Upload] 파일 크기 초과: filename=%s, size=%.2fMB, limit=%dMB",
            file.filename,
            len(file_bytes) / (1024 * 1024),
            settings.max_upload_mb,
        )
        raise HTTPException(
            status_code=413,
            detail=f"파일 크기가 최대 제한({settings.max_upload_mb}MB)을 초과했습니다.",
        )

    logger.info(
        "[Upload] 파일 수신 완료: filename=%s, size=%.2fMB, 파싱/전사 스레드 실행 시작",
        file.filename,
        len(file_bytes) / (1024 * 1024),
    )

    try:
        pages, ext, total_pages = await run_in_threadpool(
            parse_document_bytes, file_bytes, file.filename
        )
    except ValueError as exc:
        logger.warning("[Upload] 자료 파싱/전사 400 오류 (%s): %s", file.filename, exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception:
        logger.exception("[Upload] 문서/음성 파싱 실패: %s", file.filename)
        raise HTTPException(
            status_code=400,
            detail="파일을 읽거나 전사할 수 없습니다. 손상되지 않은 파일인지 확인해 주세요.",
        )

    doc_title = (title or "").strip() or file.filename.rsplit(".", 1)[0]
    if is_audio:
        content_type = get_audio_mime_type(ext)
    else:
        content_type = file.content_type or "application/octet-stream"

    logger.info(
        "[Upload] 파싱/전사 완료 (total_pages=%d), 스토리지 업로드 시작: filename=%s, content_type=%s",
        total_pages,
        file.filename,
        content_type,
    )
    try:
        file_url = await run_in_threadpool(
            store.upload_file, file_bytes, file.filename, content_type
        )
    except Exception as exc:
        logger.exception(
            "[Upload] 스토리지 파일 업로드 실패: filename=%s, size=%.2fMB, content_type=%s",
            file.filename,
            len(file_bytes) / (1024 * 1024),
            content_type,
        )
        raise HTTPException(
            status_code=502,
            detail=f"원본 파일 스토리지 저장에 실패했습니다. (파일 용량 또는 스토리지 제한 확인 필요: {exc})",
        ) from exc

    doc_record = await run_in_threadpool(
        store.create_document,
        {
            "title": doc_title,
            "category": category.strip() or "일반의학",
            "file_name": file.filename,
            "file_url": file_url,
            "file_type": ext,
            "total_pages": total_pages,
            "page_contents": pages,
        },
    )
    logger.info(
        "[Upload] 최종 완료: doc_id=%s, filename=%s, is_audio=%s, total_pages=%d, total_elapsed=%.2fs",
        doc_record.get("id"),
        file.filename,
        is_audio,
        total_pages,
        time.monotonic() - req_started_at,
    )
    return doc_record


@router.get("")
def list_documents(category: Optional[str] = None, q: Optional[str] = None):
    """학습 자료 목록 조회 (과목 및 제목 검색 지원)"""
    return {"documents": store.list_documents(category=category, query=q)}


@router.get("/local-file/{safe_name}")
def get_local_file(safe_name: str):
    """Supabase 미설정 환경에서 로컬에 저장된 원본 파일 제공"""
    path = store.get_local_file_path(safe_name)
    if not path:
        raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")
    return FileResponse(path, headers={"X-Content-Type-Options": "nosniff"})


@router.get("/{doc_id}")
def get_document(doc_id: str):
    """특정 학습 자료 상세 조회 (페이지별 원문 및 서명 URL 포함)"""
    doc = store.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="학습 자료를 찾을 수 없습니다.")
    return doc


@router.delete("/{doc_id}")
def delete_document(doc_id: str):
    """학습 자료 및 연관된 요약/문제/카드/이력/Storage 파일 삭제"""
    doc = store.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="학습 자료를 찾을 수 없습니다.")
    store.delete_document(doc_id)
    return {"deleted": True, "id": doc_id}
