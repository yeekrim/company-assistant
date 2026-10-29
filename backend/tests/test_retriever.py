import pytest
from unittest.mock import patch, MagicMock
from app.rag.retriever import search, search_chunks, add_documents, list_documents, delete_document, set_effective_date


MOCK_CHUNKS = ["휴가 신청은 MIS에서 가능합니다.", "출산휴가는 20일입니다.", "연차는 연 15일입니다."]


def make_mock_collection(chunks=None):
    col = MagicMock()
    docs = chunks or MOCK_CHUNKS
    col.query.return_value = {"documents": [docs], "metadatas": [[{"source": "test.pdf"} for _ in docs]]}
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
    col.query.return_value = {"documents": [[]], "metadatas": [[]]}
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
        assert call_kwargs["metadatas"] == [{"source": "guide.pdf", "effective_date": 0}] * 2


def test_add_documents_deletes_old_chunks_before_upsert():
    col = make_mock_collection()
    with patch("app.rag.retriever.get_collection", return_value=col), \
         patch("app.rag.retriever.embed", return_value=[[0.1] * 384]):
        add_documents(company_id=1, chunks=["청크1"], doc_name="guide.pdf")
        col.delete.assert_called_once_with(where={"source": "guide.pdf"})
        assert [c[0] for c in col.method_calls if c[0] in ("delete", "upsert")] == ["delete", "upsert"]


def test_add_documents_keeps_old_chunks_if_embedding_fails():
    col = make_mock_collection()
    with patch("app.rag.retriever.get_collection", return_value=col), \
         patch("app.rag.retriever.embed", side_effect=RuntimeError("embed 실패")):
        with pytest.raises(RuntimeError):
            add_documents(company_id=1, chunks=["청크1"], doc_name="guide.pdf")
        col.delete.assert_not_called()


def test_reupload_with_fewer_chunks_leaves_no_stale_chunks():
    """실제 (인메모리) Chroma로 재업로드 후 남은 청크를 확인한다."""
    import chromadb
    col = chromadb.EphemeralClient().create_collection("reupload_test")
    with patch("app.rag.retriever.get_collection", return_value=col), \
         patch("app.rag.retriever.embed", side_effect=lambda texts: [[0.1] * 4 for _ in texts]):
        add_documents(company_id=1, chunks=["a", "b", "c"], doc_name="guide.pdf")
        add_documents(company_id=1, chunks=["x"], doc_name="guide.pdf")
    assert col.get(where={"source": "guide.pdf"})["documents"] == ["x"]


# ── 시행일 ─────────────────────────────────────────────────────────

def _dated_collection(name):
    import chromadb
    col = chromadb.EphemeralClient().create_collection(name)
    fake_embed = lambda texts: [[0.1] * 4 for _ in texts]  # noqa: E731
    with patch("app.rag.retriever.get_collection", return_value=col), \
         patch("app.rag.retriever.embed", side_effect=fake_embed):
        add_documents(1, ["연차 15일(2016년판)"], "복무_2016.pdf", effective_date=20160101)
        add_documents(1, ["연차 11일(2023년판)"], "복무_2023.pdf", effective_date=20230101)
        add_documents(1, ["날짜 모르는 문서"], "기타.pdf")
    return col, fake_embed


def test_search_chunks_returns_source_and_date():
    col, fake_embed = _dated_collection("dated_all")
    with patch("app.rag.retriever.get_collection", return_value=col), \
         patch("app.rag.retriever.embed", side_effect=fake_embed):
        got = {c.source: c.effective_date for c in search_chunks(1, "연차", top_k=10)}
    assert got == {"복무_2016.pdf": 20160101, "복무_2023.pdf": 20230101, "기타.pdf": 0}


def test_search_chunks_as_of_excludes_later_documents():
    col, fake_embed = _dated_collection("dated_asof")
    with patch("app.rag.retriever.get_collection", return_value=col), \
         patch("app.rag.retriever.embed", side_effect=fake_embed):
        got = {c.source for c in search_chunks(1, "연차", top_k=10, as_of=20161231)}
    assert got == {"복무_2016.pdf", "기타.pdf"}  # 시행일 미상(0)은 항상 포함


def test_set_effective_date_updates_metadata_only():
    col, fake_embed = _dated_collection("dated_set")
    with patch("app.rag.retriever.get_collection", return_value=col):
        set_effective_date(1, "기타.pdf", 20200101)
        docs = {d["name"]: d["effective_date"] for d in list_documents(1)}
    assert docs["기타.pdf"] == 20200101
    assert col.get(where={"source": "기타.pdf"})["documents"] == ["날짜 모르는 문서"]


def test_set_effective_date_raises_if_not_found():
    col, _ = _dated_collection("dated_missing")
    with patch("app.rag.retriever.get_collection", return_value=col):
        with pytest.raises(ValueError, match="찾을 수 없습니다"):
            set_effective_date(1, "없음.pdf", 20200101)


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
