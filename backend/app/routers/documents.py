import logging
from typing import Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
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
    if not file.filename:
        raise HTTPException(status_code=400, detail="파일명이 비어 있습니다.")

    try:
        validate_file_extension(file.filename)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    max_bytes = settings.max_upload_mb * 1024 * 1024
    file_bytes = await file.read(max_bytes + 1)
    if not file_bytes:
        raise HTTPException(status_code=400, detail="빈 파일은 업로드할 수 없습니다.")
    if len(file_bytes) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"파일 크기가 최대 제한({settings.max_upload_mb}MB)을 초과했습니다.",
        )

    try:
        pages, ext, total_pages = parse_document_bytes(file_bytes, file.filename)
    except ValueError as exc:
        logger.warning("자료 업로드 파싱 400 오류 (%s): %s", file.filename, exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception:
        logger.exception("문서/음성 파싱 실패: %s", file.filename)
        raise HTTPException(
            status_code=400,
            detail="파일을 읽거나 전사할 수 없습니다. 손상되지 않은 파일인지 확인해 주세요.",
        )

    doc_title = (title or "").strip() or file.filename.rsplit(".", 1)[0]
    if is_audio_extension(ext):
        content_type = get_audio_mime_type(ext)
    else:
        content_type = file.content_type or "application/octet-stream"
    file_url = store.upload_file(file_bytes, file.filename, content_type)

    doc_record = store.create_document({
        "title": doc_title,
        "category": category.strip() or "일반의학",
        "file_name": file.filename,
        "file_url": file_url,
        "file_type": ext,
        "total_pages": total_pages,
        "page_contents": pages,
    })
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
