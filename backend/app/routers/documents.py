from typing import Optional
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from app.services.document_parser import parse_document_bytes
from app.services.supabase_service import store

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    title: Optional[str] = Form(default=None),
    category: str = Form(default="일반의학"),
):
    """학습 자료(PDF, DOCX, PPTX, TXT) 업로드 및 페이지별 텍스트 파싱"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="파일명이 비어 있습니다.")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="빈 파일은 업로드할 수 없습니다.")

    try:
        pages, ext, total_pages = parse_document_bytes(file_bytes, file.filename)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"문서 파싱 중 오류가 발생했습니다: {exc}") from exc

    doc_title = (title or "").strip() or file.filename.rsplit(".", 1)[0]
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
    return FileResponse(path)


@router.get("/{doc_id}")
def get_document(doc_id: str):
    """특정 학습 자료 상세 조회 (페이지별 원문 포함)"""
    doc = store.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="학습 자료를 찾을 수 없습니다.")
    return doc


@router.delete("/{doc_id}")
def delete_document(doc_id: str):
    """학습 자료 및 연관된 요약/문제/카드/이력 삭제"""
    doc = store.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="학습 자료를 찾을 수 없습니다.")
    store.delete_document(doc_id)
    return {"deleted": True, "id": doc_id}
