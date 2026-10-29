import pytest
from app.rag.chunker import chunk_text, extract_text
import tempfile, os


# ── chunk_text 단위 테스트 ──────────────────────────────────────────

def test_chunk_size_does_not_exceed_limit():
    text = "가" * 2000
    chunks = chunk_text(text, chunk_size=500, overlap=50)
    for chunk in chunks:
        assert len(chunk) <= 500


def test_chunk_count_is_correct():
    text = "나" * 1000
    chunks = chunk_text(text, chunk_size=500, overlap=50)
    # (1000-500)/(500-50) + 1 = 약 2개
    assert len(chunks) >= 2


def test_overlap_preserves_context():
    text = "A" * 500 + "B" * 500
    chunks = chunk_text(text, chunk_size=500, overlap=50)
    # 두 번째 청크 앞부분에 첫 번째 청크 끝부분(A)이 포함돼야 함
    assert "A" in chunks[1]


def test_empty_text_returns_empty_list():
    assert chunk_text("") == []
    assert chunk_text("   ") == []


def test_short_text_returns_single_chunk():
    text = "짧은 텍스트"
    chunks = chunk_text(text)
    assert len(chunks) == 1
    assert chunks[0] == text


def test_chunk_covers_all_content():
    text = "테스트" * 300
    chunks = chunk_text(text, chunk_size=500, overlap=50)
    # 모든 청크를 합쳤을 때 원본 내용이 포함돼야 함
    merged = "".join(chunks)
    assert "테스트" in merged


# ── extract_text 단위 테스트 ────────────────────────────────────────

def test_extract_text_from_txt():
    content = "사내 공지사항 테스트 텍스트입니다."
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write(content)
        path = f.name
    try:
        result = extract_text(path)
        assert content in result
    finally:
        os.unlink(path)


def test_extract_text_from_docx():
    import docx
    content = "DOCX 테스트 문서입니다."
    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
        path = f.name
    doc = docx.Document()
    doc.add_paragraph(content)
    doc.save(path)
    try:
        result = extract_text(path)
        assert content in result
    finally:
        os.unlink(path)


# ── 조문 단위 청킹 ──────────────────────────────────────────────

REGULATION = """국가공무원 복무규정
제1조(목적) 이 영은 복무에 관한 사항을 규정한다.
제2조(선서) ① 공무원은 선서를 하여야 한다.
② 선서는 별표 1에 따른다.
제20조(특별휴가) ① 경조사휴가를 주어야 한다.
② 임신 중인 공무원은 90일(미숙아는 100일)의 출산휴가를 사용할 수 있다. 다만, 다음 각 호의 어느 하나에 해당하면 나누어 쓸 수 있다.
1. 유산ㆍ사산의 경험이 있는 경우
2. 40세 이상인 경우
부칙<대통령령 제1호, 1970. 6. 15.>
제2조(출산휴가에 관한 적용례) 제20조제2항은 미숙아를 출산하는 경우부터 적용한다.
별표 1을 다음과 같이 한다.
[별표 1]
선서문
[별표 2] 국내 여비 지급표(제16조 관련)
[별표 2] 국내 여비 지급표(제16조 관련)
숙박비 상한액: 서울특별시 70,000
"""


def test_article_chunks_keep_paragraph_with_its_items():
    chunks = chunk_text(REGULATION, chunk_size=120)
    leave = [c for c in chunks if "90일" in c]
    assert len(leave) == 1
    assert "1. 유산" in leave[0] and "2. 40세" in leave[0]  # 항 아래 호가 같은 청크에 있다


def test_split_article_chunks_are_prefixed_with_article_title():
    chunks = chunk_text(REGULATION, chunk_size=120)
    leave = next(c for c in chunks if "90일" in c)
    assert leave.startswith("제20조(특별휴가) ② 임신 중인")


def test_addenda_are_skipped_but_appendix_after_them_is_kept():
    joined = "\n".join(chunk_text(REGULATION, chunk_size=120))
    assert "적용례" not in joined and "대통령령 제1호" not in joined
    assert "선서문" not in joined  # 부칙의 "별표 1을 다음과 같이 한다." 뒤 [별표 1]은 인용이라 부칙의 일부
    assert "서울특별시 70,000" in joined
    assert joined.count("[별표 2] 국내 여비 지급표") == 1  # 반복된 별표 제목은 한 번만


def test_article_chunks_do_not_exceed_size_plus_title():
    for c in chunk_text(REGULATION * 3, chunk_size=60):
        assert len(c) <= 60 + len("제20조(특별휴가) ")


def test_plain_document_still_uses_character_chunks():
    text = "가" * 1200
    assert chunk_text(text) == [text[0:500], text[450:950], text[900:1200]]


def test_main_articles_after_leading_addenda_are_kept():
    # 개정 이력(부칙)을 문서 맨 앞에 두는 사규
    text = "부칙<2024. 10. 23.>\n이 규정은 2024년 10월 28일부터 시행한다.\n제1조(시행일) 공포한 날부터 시행한다.\n" \
           "제1조(목적) 이 규정은 여비 지급을 정한다.\n제2조(정의) 여비란 운임을 말한다.\n제3조(지급) 여비는 별표에 따른다.\n" \
           "<별표 1> 국내여비\n숙박비 70,000"
    joined = "\n".join(chunk_text(text))
    assert "공포한 날부터" not in joined and "2024년 10월 28일" not in joined
    assert "제1조(목적)" in joined and "제3조(지급)" in joined and "숙박비 70,000" in joined
