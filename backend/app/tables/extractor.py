"""문서 속 표를 구조 그대로 추출한다.

chunker는 표를 텍스트로 펼쳐 청킹하지만(RAG 검색용), 여기서는 행·열과 타입을 보존해
SQL 계산에 쓸 수 있게 한다.
"""
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import docx
import pdfplumber

NUM = re.compile(r"^-?\d{1,3}(,\d{3})+(\.\d+)?$|^-?\d+(\.\d+)?$")
DATE = re.compile(r"^(\d{4})[-./](\d{1,2})[-./](\d{1,2})\.?$")


@dataclass
class ExtractedTable:
    title: str
    columns: list[str]
    rows: list[list] = field(default_factory=list)


def extract_tables(file_path: str) -> list[ExtractedTable]:
    suffix = Path(file_path).suffix.lower()
    if suffix == ".pdf":
        return assemble(_pdf_tables(file_path))
    if suffix == ".docx":
        return assemble(_docx_tables(file_path))
    return []


def _pdf_tables(file_path: str) -> list[tuple[str, list[list]]]:
    out = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            for t in page.find_tables():
                # 표 바로 위 텍스트의 마지막 줄을 제목으로 사용 (예: "부록 1. 경비 내역")
                title = ""
                if t.bbox[1] > 1:
                    above = page.within_bbox((0, 0, page.width, t.bbox[1])).extract_text() or ""
                    lines = [l for l in above.splitlines() if l.strip()]
                    title = lines[-1].strip() if lines else ""
                out.append((title, t.extract()))
    return out


def _docx_tables(file_path: str) -> list[tuple[str, list[list]]]:
    doc = docx.Document(file_path)
    return [("", [[cell.text for cell in row.cells] for row in table.rows]) for table in doc.tables]


def _clean(cell) -> str:
    return (cell or "").replace("\n", " ").strip()


def _header(cells: list[str]) -> list[str]:
    """빈 헤더는 '열N'으로, 중복 헤더는 '_2' 등을 붙여 고유하게 만든다."""
    seen: dict[str, int] = {}
    out = []
    for i, c in enumerate(cells, 1):
        name = c or f"열{i}"
        if name in seen:
            seen[name] += 1
            name = f"{name}_{seen[name]}"
        else:
            seen[name] = 1
        out.append(name)
    return out


def assemble(raw_tables: list[tuple[str, list[list]]]) -> list[ExtractedTable]:
    """원시 표 목록 → 정리된 표 목록.

    - 첫 행을 헤더로 사용, 빈 행 제거, 헤더만 있는 표는 버림
    - 바로 앞 표와 헤더가 같으면 페이지를 넘어 이어지는 표로 보고 합침
    - 열마다 숫자/날짜 타입 변환
    """
    tables: list[ExtractedTable] = []
    for title, raw in raw_tables:
        rows = [[_clean(c) for c in r] for r in raw if any(_clean(c) for c in r)]
        if len(rows) < 2:
            continue
        header = _header(rows[0])
        body = [(r + [""] * len(header))[:len(header)] for r in rows[1:]]
        if tables and tables[-1].columns == header:
            tables[-1].rows.extend(body)
        else:
            tables.append(ExtractedTable(title or f"표 {len(tables) + 1}", header, body))

    for t in tables:
        cols = [_coerce([r[j] for r in t.rows]) for j in range(len(t.columns))]
        t.rows = [list(r) for r in zip(*cols)]
    return tables


def _coerce(col: list[str]) -> list:
    """열 전체가 숫자면 int/float, 날짜면 date로 변환. 하나라도 아니면 문자열 유지."""
    vals = [v for v in col if v != ""]
    if not vals:
        return [None] * len(col)
    if all(NUM.match(v) for v in vals):
        nums = [float(v.replace(",", "")) if v else None for v in col]
        if all(n is None or n.is_integer() for n in nums):
            return [int(n) if n is not None else None for n in nums]
        return nums
    if all(DATE.match(v) for v in vals):
        out = []
        for v in col:
            m = DATE.match(v) if v else None
            try:
                out.append(date(int(m[1]), int(m[2]), int(m[3])) if m else None)
            except ValueError:  # 2026-02-30 같은 잘못된 날짜가 섞이면 문자열로 둠
                return [v or None for v in col]
        return out
    return [v or None for v in col]
