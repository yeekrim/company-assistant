import pytest
from unittest.mock import patch, MagicMock
from app.rag.retriever import search, add_documents, list_documents, delete_document


MOCK_CHUNKS = ["휴가 신청은 MIS에서 가능합니다.", "출산휴가는 20일입니다.", "연차는 연 15일입니다."]


def make_mock_collection(chunks=None):
    col = MagicMock()
    col.query.return_value = {"documents": [chunks or MOCK_CHUNKS]}
    col.get.return_value = {
        "ids": ["doc_0", "doc_1"],
        "metadatas": [{"source": "test.pdf"}, {"source": "test.pdf"}],
    }
    return col


# ── search ────────────────────────────────────────────────────────

def test_search_returns_list_of_strings():
    with patch("app.rag.retriever.get_collection", return_value=make_mock_collection()), \
         patch("app.rag.retriever.embed", return_value=[[0.1] * 384]):
        result = search(company_id=1, query="휴가 신청")
        assert isinstance(result, list)
        assert all(isinstance(r, str) for r in result)


def test_search_returns_correct_chunks():
    with patch("app.rag.retriever.get_collection", return_value=make_mock_collection()), \
         patch("app.rag.retriever.embed", return_value=[[0.1] * 384]):
        result = search(company_id=1, query="휴가")
        assert result == MOCK_CHUNKS


def test_search_empty_collection_returns_empty():
    col = make_mock_collection(chunks=[])
    col.query.return_value = {"documents": [[]]}
    with patch("app.rag.retriever.get_collection", return_value=col), \
         patch("app.rag.retriever.embed", return_value=[[0.1] * 384]):
        result = search(company_id=1, query="없는내용")
        assert result == []


def test_search_respects_top_k():
    col = make_mock_collection()
    with patch("app.rag.retriever.get_collection", return_value=col), \
         patch("app.rag.retriever.embed", return_value=[[0.1] * 384]):
        search(company_id=1, query="테스트", top_k=3)
        col.query.assert_called_once()
        call_kwargs = col.query.call_args.kwargs
        assert call_kwargs["n_results"] == 3


# ── add_documents ─────────────────────────────────────────────────

def test_add_documents_calls_upsert_with_correct_data():
    col = make_mock_collection()
    chunks = ["청크1", "청크2"]
    with patch("app.rag.retriever.get_collection", return_value=col), \
         patch("app.rag.retriever.embed", return_value=[[0.1] * 384, [0.2] * 384]):
        add_documents(company_id=1, chunks=chunks, doc_name="guide.pdf")
        col.upsert.assert_called_once()
        call_kwargs = col.upsert.call_args.kwargs
        assert call_kwargs["ids"] == ["guide.pdf_0", "guide.pdf_1"]
        assert call_kwargs["documents"] == chunks
        assert call_kwargs["metadatas"] == [{"source": "guide.pdf"}, {"source": "guide.pdf"}]


# ── list_documents ────────────────────────────────────────────────

def test_list_documents_returns_unique_sources():
    with patch("app.rag.retriever.get_collection", return_value=make_mock_collection()):
        result = list_documents(company_id=1)
        assert isinstance(result, list)
        names = [d["name"] for d in result]
        assert "test.pdf" in names
        assert len(names) == len(set(names))  # 중복 없음


# ── delete_document ───────────────────────────────────────────────

def test_delete_document_calls_collection_delete():
    col = make_mock_collection()
    with patch("app.rag.retriever.get_collection", return_value=col):
        delete_document(company_id=1, doc_name="test.pdf")
        col.delete.assert_called_once_with(ids=["doc_0", "doc_1"])


def test_delete_document_raises_if_not_found():
    col = make_mock_collection()
    col.get.return_value = {"ids": [], "metadatas": []}
    with patch("app.rag.retriever.get_collection", return_value=col):
        with pytest.raises(ValueError, match="찾을 수 없습니다"):
            delete_document(company_id=1, doc_name="없는파일.pdf")
