"""비교할 검색 설정. 설정 = "회사 문서를 어떤 청크로 색인하나" + "몇 개를 가져오나".

- A (current): 지금 앱의 업로드 경로 그대로. 문서마다 표 행도 텍스트로 펼쳐 500자씩 청킹
- B (table_split): 문서마다 표를 뺀 본문만 청킹 + 표마다 요약 한 줄
  sql_harness의 kaizen-go 인덱스와 같지만 본문 앞의 "[문서: …]" 접두어는 뺐다.
  접두어가 임베딩 128토큰 중 일부를 차지해 순위를 바꾸므로(2026-10-07 리포트),
  표 분리 효과만 보려고 제거했다.

새 설정(R1 토큰 청킹, R2 리랭커 등)은 CONFIGS에 함수를 추가하면 pool.py와 evaluate.py가 함께 쓴다.
"""
import sys
from pathlib import Path

HARNESS = Path(__file__).resolve().parent.parent / "sql_harness"
sys.path.append(str(HARNESS))  # 뒤에 붙여야 이 폴더의 questions.py가 sql_harness 것에 가려지지 않음

from common import DocIndex  # noqa: E402  (backend를 sys.path에 넣고 cwd를 backend로 바꿈)

import pdfplumber  # noqa: E402

from app.rag.chunker import chunk_text, extract_text  # noqa: E402
from app.tables.extractor import ExtractedTable, assemble  # noqa: E402

from companies import docs  # noqa: E402

TOP_K = 10


def extract(pdf_path: str) -> tuple[str, list[ExtractedTable]]:
    """(표를 제외한 본문 텍스트, 표 목록). sql_harness/tables.extract와 같은 방식이다.
    다만 실제 PDF에는 표 영역이 페이지 밖까지 잡히는 경우가 있어(pdfplumber가 ValueError),
    표 영역을 페이지 안으로 잘라서 뺀다."""
    texts, raw = [], []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            found = page.find_tables()
            x0, top, x1, bottom = page.bbox
            outside = page
            for t in found:
                b = t.bbox
                clipped = (max(b[0], x0), max(b[1], top), min(b[2], x1), min(b[3], bottom))
                if clipped[0] < clipped[2] and clipped[1] < clipped[3]:
                    outside = outside.outside_bbox(clipped)
            page_text = (outside.extract_text() or "").strip()
            if page_text:
                texts.append(page_text)
            title = page_text.splitlines()[-1] if page_text else ""
            raw += [(title, t.extract()) for t in found]
    return "\n\n".join(texts), assemble(raw)


def chunks_current(paths: list[Path]) -> list[str]:
    return [c for p in paths for c in chunk_text(extract_text(str(p)))]


def chunks_table_split(paths: list[Path]) -> list[str]:
    out = []
    for p in paths:
        body, tables = extract(str(p))
        out += chunk_text(body)
        out += [f"[표] {tb.title} — 컬럼: {', '.join(tb.columns)} ({len(tb.rows)}행)" for tb in tables]
    return out


CONFIGS = {
    "A_current": chunks_current,
    "B_table_split": chunks_table_split,
}


def build(name: str, company: str) -> DocIndex:
    paths = docs(company)
    missing = [p for p in paths if not p.exists()]
    if missing:
        sys.exit("문서가 없습니다:\n" + "\n".join(map(str, missing)) +
                 "\n경비 PDF가 없으면 make_corpus.py를 먼저 실행하세요.")
    return DocIndex(CONFIGS[name](paths))
