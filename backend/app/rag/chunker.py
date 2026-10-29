import re

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


_ARTICLE = re.compile(r"^(제\d+조(?:의\d+)?\s*\([^)]*\))")  # 제20조(특별휴가)
_APPENDIX = re.compile(r"^([\[<]\s*별\s*표\s*\d+.*)")          # [별표 2] 국내 여비 지급표, [별표 1_국내여비정액표], <별표 1>
_QUOTES_APPENDIX = re.compile(r"별표\s*\d+\s*을\s*다음과\s*같이")   # 부칙의 "별표 1을 다음과 같이 한다." 뒤 [별표 1]은 인용
_ADDENDA = re.compile(r"^부\s*칙")
_PARAGRAPH = re.compile(r"^[①-⑳]")
# 부칙 안의 조문 제목. 이런 제목이 아닌 조문(제1조(목적) 등)이 나오면 부칙이 끝나고 본문이 시작된 것으로 본다.
# 개정 이력을 문서 맨 앞에 두는 사규가 있어서, 부칙 뒤를 모두 버리면 본문까지 빠진다.
_ADDENDA_TITLE = re.compile(r"시행일|경과조치|적용례|특례|다른 법령|유효기간|폐지")


# 임베딩 모델(paraphrase-multilingual-MiniLM-L12-v2)은 앞 128토큰만 읽는다. 한국어 조문으로 약 240자.
# 조문 청크는 그 안에 들어가게 250자로 자른다 (c4 평가에서 검색 적중 10/12 → 12/12, chunk_recall.py).
# 일반 문서는 측정 전이라 기존 500자를 유지한다.
ARTICLE_CHUNK_SIZE = 250
CHAR_CHUNK_SIZE = 500


def chunk_text(text: str, chunk_size: int | None = None, overlap: int = 50) -> list[str]:
    """법령·사규처럼 조문(제N조)으로 된 문서는 조문 경계로, 그 밖의 문서는 문자 단위로 청킹."""
    text = text.strip()
    if not text:
        return []
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if sum(1 for line in lines if _ARTICLE.match(line)) < 3:
        return chunk_chars(text, chunk_size or CHAR_CHUNK_SIZE, overlap)
    return chunk_articles(lines, chunk_size or ARTICLE_CHUNK_SIZE, overlap)


def chunk_chars(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """문자 단위로 청킹. overlap으로 문맥 연결."""
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks


def chunk_articles(lines: list[str], chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """조문·별표 단위로 묶고, 길면 항(①②…)과 줄 경계에서 나눈다.

    - 부칙(개정 이력·경과조치)은 색인하지 않는다. 단어만 겹쳐 본문 조문을 밀어내기 때문이다.
      부칙 뒤의 별표(요율표 등)와, 부칙 다음에 다시 시작하는 본문 조문은 색인한다.
    - 조문이 여러 청크로 나뉘면 뒤 청크 앞에 조문 제목을 붙여 어느 조문인지 알 수 있게 한다.
    """
    blocks: list[tuple[str, list[str]]] = []  # (제목, 줄)
    in_addenda = False
    prev = ""
    for line in lines:
        article, appendix = _ARTICLE.match(line), _APPENDIX.match(line)
        quoted, prev = in_addenda and bool(_QUOTES_APPENDIX.search(prev)), line
        if appendix and not quoted:
            in_addenda = False
            if blocks and blocks[-1][0] == appendix.group(1):  # 같은 별표 제목이 여러 줄 반복되면 하나로
                continue
            blocks.append((appendix.group(1), [line]))
        elif _ADDENDA.match(line):
            in_addenda = True
        elif article and not (in_addenda and _ADDENDA_TITLE.search(article.group(1))):
            in_addenda = False
            blocks.append((article.group(1), [line]))
        elif in_addenda:
            continue
        elif blocks:
            blocks[-1][1].append(line)
        else:
            blocks.append(("", [line]))

    chunks = []
    for title, block in blocks:
        units: list[str] = []  # 항 단위. 항 표시가 없는 줄(호·목·표 행)은 앞 항에 붙인다
        for line in block:
            if units and not _PARAGRAPH.match(line):
                units[-1] += "\n" + line
            else:
                units.append(line)
        chunks += _pack(title, units, chunk_size, overlap)
    return chunks


def _pack(title: str, units: list[str], chunk_size: int, overlap: int) -> list[str]:
    """항을 chunk_size 안에서 이어 붙인다. 한 항이 넘치면 줄 단위로, 한 줄이 넘치면 문자 단위로 나눈다."""
    pieces = []
    for unit in units:
        if len(unit) <= chunk_size:
            pieces.append(unit)
            continue
        for line in unit.split("\n"):
            pieces += [line] if len(line) <= chunk_size else chunk_chars(line, chunk_size, overlap)

    chunks, current = [], ""
    for piece in pieces:
        head = f"{title} " if title and chunks and not current else ""
        if current and len(current) + 1 + len(piece) > chunk_size:
            chunks.append(current)
            current = f"{title} {piece}" if title else piece
        else:
            current = f"{current}\n{piece}" if current else head + piece
    if current:
        chunks.append(current)
    return chunks
