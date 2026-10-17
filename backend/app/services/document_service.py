import logging
import os
import tempfile
from fastapi import UploadFile
from app.rag.chunker import extract_text, chunk_text
from app.rag.retriever import add_documents
from app.tables.extractor import extract_tables
from app.tables.store import save_tables

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}

async def process_upload(file: UploadFile, company_id: int) -> dict:
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"지원하지 않는 파일 형식입니다: {ext}")

    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        text = extract_text(tmp_path)
        chunks = chunk_text(text)
        add_documents(company_id, chunks, doc_name=file.filename)
        tables = _store_tables(tmp_path, company_id, file.filename)
    finally:
        os.unlink(tmp_path)

    return {"filename": file.filename, "chunks": len(chunks), "tables": tables}


def _store_tables(path: str, company_id: int, doc_name: str) -> int:
    """문서 속 표를 구조화해 저장. 실패해도 업로드(RAG 색인)는 성공으로 둔다."""
    try:
        return len(save_tables(company_id, doc_name, extract_tables(path)))
    except Exception:
        logger.exception("표 저장 실패: company=%s doc=%s", company_id, doc_name)
        return 0
