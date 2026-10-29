"""PDF에서 본문 텍스트(표 제외)와 표를 분리해 꺼낸다.

표 정리(헤더·병합·타입 변환)는 앱의 `app.tables.extractor.assemble`을 그대로 써서,
실험 결과가 실제 앱 코드의 동작을 반영하도록 한다.
"""
from pathlib import Path

import pdfplumber

from app.tables.extractor import ExtractedTable, assemble  # noqa: F401  (common.py가 sys.path 설정)


def extract(pdf_path: str) -> tuple[str, list[ExtractedTable]]:
    """(표를 제외한 본문 텍스트, 표 목록)을 반환."""
    texts, raw = [], []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            found = page.find_tables()
            outside = page
            for t in found:
                outside = outside.outside_bbox(t.bbox)
            page_text = (outside.extract_text() or "").strip()
            if page_text:
                texts.append(page_text)
            title = page_text.splitlines()[-1] if page_text else ""
            raw += [(title, t.extract()) for t in found]
    return "\n\n".join(texts), assemble(raw)


def extract_many(paths: list[Path]) -> tuple[str, list[ExtractedTable]]:
    """여러 문서: 본문은 문서 이름을 머리에 붙여 잇고, 표 제목에도 문서 이름을 붙인다."""
    bodies, tables = [], []
    for p in paths:
        text, ts = extract(str(p))
        bodies.append(f"[문서: {p.stem}]\n{text}")
        for t in ts:
            t.title = f"{p.stem} — {t.title}"
        tables += ts
    return "\n\n".join(bodies), tables
