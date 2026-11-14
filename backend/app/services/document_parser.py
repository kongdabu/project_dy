import io
from typing import Tuple
import pymupdf
from docx import Document as DocxDocument
from pptx import Presentation


def parse_document_bytes(file_bytes: bytes, filename: str) -> Tuple[list[dict], str, int]:
    """
    업로드된 파일 바이트(PDF, DOCX, PPTX, TXT/MD)에서 페이지/슬라이드별 텍스트를 추출한다.

    Args:
        file_bytes: 원본 파일 바이너리
        filename: 원본 파일명

    Returns:
        (페이지별 텍스트 리스트, 파일 확장자, 전체 페이지 수)
    """
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "txt"
    pages: list[dict] = []

    if ext == "pdf":
        with pymupdf.open(stream=file_bytes, filetype="pdf") as pdf_doc:
            for idx, page in enumerate(pdf_doc, start=1):
                text = page.get_text("text").strip()
                pages.append({"page": idx, "text": text})
        total_pages = len(pages) if pages else 1
        return pages, ext, total_pages

    if ext == "pptx":
        prs = Presentation(io.BytesIO(file_bytes))
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
            pages.append({"page": (idx // chunk_size) + 1, "text": decoded[idx : idx + chunk_size]})
    return pages, ext, len(pages)
