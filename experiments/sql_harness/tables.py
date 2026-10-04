"""PDF에서 표를 '구조 그대로' 꺼낸다 (현재 chunker는 표를 텍스트로 펼쳐 500자씩 자름).

- 페이지마다 반복되는 같은 헤더의 표는 하나로 합친다.
- 표 바로 위 텍스트(예: '부록 1. ...')를 표 제목으로 쓴다.
- '12,300' 같은 문자열은 숫자로, 'YYYY-MM-DD'는 날짜로 변환한다.
"""
import re
from dataclasses import dataclass
from datetime import date

import pdfplumber

NUM = re.compile(r"^-?[\d,]+(\.\d+)?$")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@dataclass
class ExtractedTable:
    title: str
    columns: list[str]
    rows: list[list]


def _coerce(col: list[str]):
    vals = [v for v in col if v != ""]
    if vals and all(NUM.match(v) for v in vals):
        nums = [float(v.replace(",", "")) if v else None for v in col]
        if all(n is None or n.is_integer() for n in nums):
            return [int(n) if n is not None else None for n in nums]
        return nums
    if vals and all(DATE.match(v) for v in vals):
        return [date.fromisoformat(v) if v else None for v in col]
    return col


def extract(pdf_path: str) -> tuple[str, list[ExtractedTable]]:
    """(표를 제외한 본문 텍스트, 표 목록)을 반환."""
    texts, tables = [], []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            found = page.find_tables()
            outside = page
            for t in found:
                outside = outside.outside_bbox(t.bbox)
            page_text = (outside.extract_text() or "").strip()
            if page_text:
                texts.append(page_text)
            for t in found:
                raw = [[(c or "").replace("\n", " ").strip() for c in row] for row in t.extract()]
                header, body = raw[0], raw[1:]
                if tables and tables[-1].columns == header:  # 다음 페이지로 이어지는 표
                    tables[-1].rows.extend(body)
                else:
                    title = page_text.splitlines()[-1] if page_text else f"표 {len(tables) + 1}"
                    tables.append(ExtractedTable(title, header, body))
    for t in tables:
        cols = list(zip(*t.rows)) if t.rows else [[] for _ in t.columns]
        t.rows = [list(r) for r in zip(*[_coerce(list(c)) for c in cols])]
    return "\n\n".join(texts), tables
