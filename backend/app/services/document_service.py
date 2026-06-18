import os
import tempfile
from fastapi import UploadFile
from app.rag.chunker import extract_text, chunk_text
from app.rag.retriever import add_documents

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
    finally:
        os.unlink(tmp_path)

    return {"filename": file.filename, "chunks": len(chunks)}
