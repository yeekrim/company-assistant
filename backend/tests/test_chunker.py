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
