import io
from typing import Tuple
import pymupdf
from docx import Document as DocxDocument
from pptx import Presentation
from app.config import settings

ALLOWED_EXTENSIONS = {"pdf", "docx", "doc", "pptx", "txt", "md"}


def validate_file_extension(filename: str) -> str:
    """허용된 학습 자료 확장자인지 검증한다."""
    if "." not in filename:
        raise ValueError("파일 확장자가 없습니다. (허용: PDF, DOCX, PPTX, TXT, MD)")
    ext = filename.rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"지원하지 않는 파일 형식(.{ext})입니다. (허용: PDF, DOCX, PPTX, TXT, MD)")
    return ext


def parse_document_bytes(file_bytes: bytes, filename: str) -> Tuple[list[dict], str, int]:
    """
    업로드된 파일 바이트(PDF, DOCX, PPTX, TXT/MD)에서 페이지/슬라이드별 텍스트를 추출한다.
    최대 페이지 수 제한을 초과하면 예외를 발생시킨다.
    """
    ext = validate_file_extension(filename)
    pages: list[dict] = []
    max_pages = settings.max_document_pages

    if ext == "pdf":
        with pymupdf.open(stream=file_bytes, filetype="pdf") as pdf_doc:
            if len(pdf_doc) > max_pages:
                raise ValueError(f"PDF 최대 페이지 제한({max_pages}페이지)을 초과했습니다.")
            for idx, page in enumerate(pdf_doc, start=1):
                text = page.get_text("text").strip()
                pages.append({"page": idx, "text": text})
        total_pages = len(pages) if pages else 1
        return pages, ext, total_pages

    if ext == "pptx":
        prs = Presentation(io.BytesIO(file_bytes))
        if len(prs.slides) > max_pages:
            raise ValueError(f"PPTX 최대 슬라이드 제한({max_pages}장)을 초과했습니다.")
        for idx, slide in enumerate(prs.slides, start=1):
            slide_texts: list[str] = []
            for shape in slide.shapes:
                if shape.has_text_frame:
                    text = shape.text_frame.text.strip()
                    if text:
                        slide_texts.append(text)
                if shape.has_table:
                    for row in shape.table.rows:
                        row_text = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
                        if row_text:
                            slide_texts.append(row_text)
            pages.append({"page": idx, "text": "\n".join(slide_texts)})
        if not pages:
            pages.append({"page": 1, "text": ""})
        return pages, ext, len(pages)

    if ext in ("docx", "doc"):
        doc = DocxDocument(io.BytesIO(file_bytes))
        paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        chunk_size = 1500
        current_chunk: list[str] = []
        current_len = 0
        page_num = 1
        for para in paragraphs:
            current_chunk.append(para)
            current_len += len(para)
            if current_len >= chunk_size:
                pages.append({"page": page_num, "text": "\n".join(current_chunk)})
                page_num += 1
                if page_num > max_pages:
                    raise ValueError(f"문서 최대 분량 제한({max_pages}페이지)을 초과했습니다.")
                current_chunk = []
                current_len = 0
        if current_chunk:
            pages.append({"page": page_num, "text": "\n".join(current_chunk)})
        if not pages:
            pages.append({"page": 1, "text": ""})
        return pages, ext, len(pages)

    # TXT, MD 등 일반 텍스트 파일 처리
    decoded = file_bytes.decode("utf-8", errors="replace").strip()
    chunk_size = 1500
    if not decoded:
        pages.append({"page": 1, "text": ""})
    else:
        for idx in range(0, len(decoded), chunk_size):
            if len(pages) >= max_pages:
                raise ValueError(f"텍스트 최대 분량 제한({max_pages}페이지)을 초과했습니다.")
            pages.append({"page": (idx // chunk_size) + 1, "text": decoded[idx : idx + chunk_size]})
    return pages, ext, len(pages)
