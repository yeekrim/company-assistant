import pdfplumber
import docx
from pathlib import Path

def extract_text(file_path: str) -> str:
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix == ".pdf":
        pages = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                parts = []
                text = page.extract_text()
                if text:
                    parts.append(text)
                for table in page.extract_tables():
                    rows = []
                    headers = None
                    for row in table:
                        cells = [cell.strip().replace("\n", " ") if cell else "" for cell in row]
                        # 첫 행이 헤더인지 판단 (모든 셀이 비어있지 않으면 헤더로 간주)
                        if headers is None:
                            if all(cells):
                                headers = cells
                                continue
                            else:
                                headers = []
                        if headers and len(headers) == len(cells):
                            rows.append(" / ".join(f"{h}: {v}" for h, v in zip(headers, cells) if v))
                        else:
                            rows.append(" | ".join(cells))
                    parts.append("\n".join(rows))
                pages.append("\n".join(parts))
        return "\n\n".join(pages)

    if suffix == ".docx":
        doc = docx.Document(file_path)
        return "\n".join(p.text for p in doc.paragraphs)

    # .txt / .md
    return path.read_text(encoding="utf-8")


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """문자 단위로 청킹. overlap으로 문맥 연결."""
    text = text.strip()
    if not text:
        return []

    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])
        start += chunk_size - overlap

    return chunks
