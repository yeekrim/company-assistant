from typing import NamedTuple

import chromadb
from app.core.config import settings
from app.rag.dates import UNKNOWN
from app.rag.embedder import embed


class Chunk(NamedTuple):
    text: str
    source: str
    effective_date: int  # YYYYMMDD, 모르면 0


_client = None

def get_client():
    global _client
    if _client is None:
        _client = chromadb.HttpClient(host=settings.CHROMA_HOST, port=settings.CHROMA_PORT)
    return _client

def get_collection(company_id: int):
    """회사별로 독립된 컬렉션 사용."""
    client = get_client()
    return client.get_or_create_collection(
        name=f"company_{company_id}",
        metadata={"hnsw:space": "cosine"},
    )

def add_documents(company_id: int, chunks: list[str], doc_name: str, effective_date: int = UNKNOWN):
    collection = get_collection(company_id)
    embeddings = embed(chunks)
    # 같은 문서 재업로드 시 청크 수가 줄면 옛 청크가 남으므로 먼저 지운다 (임베딩 실패 시 기존 문서 유지)
    collection.delete(where={"source": doc_name})
    ids = [f"{doc_name}_{i}" for i in range(len(chunks))]
    collection.upsert(
        ids=ids,
        embeddings=embeddings,
        documents=chunks,
        metadatas=[{"source": doc_name, "effective_date": effective_date} for _ in chunks],
    )

def list_documents(company_id: int) -> list[dict]:
    collection = get_collection(company_id)
    result = collection.get(include=["metadatas"])
    seen: dict[str, dict] = {}
    for meta in result["metadatas"]:
        src = meta.get("source", "unknown")
        doc = seen.setdefault(src, {"name": src, "chunks": 0,
                                    "effective_date": meta.get("effective_date", UNKNOWN)})
        doc["chunks"] += 1
    return list(seen.values())


def set_effective_date(company_id: int, doc_name: str, effective_date: int):
    """이미 올라간 문서의 시행일만 바꾼다. 텍스트·임베딩은 그대로."""
    collection = get_collection(company_id)
    result = collection.get(where={"source": doc_name}, include=["metadatas"])
    if not result["ids"]:
        raise ValueError(f"'{doc_name}' 문서를 찾을 수 없습니다.")
    collection.update(
        ids=result["ids"],
        metadatas=[{**m, "effective_date": effective_date} for m in result["metadatas"]],
    )

def delete_document(company_id: int, doc_name: str):
    collection = get_collection(company_id)
    result = collection.get(where={"source": doc_name}, include=["metadatas"])
    if not result["ids"]:
        raise ValueError(f"'{doc_name}' 문서를 찾을 수 없습니다.")
    collection.delete(ids=result["ids"])

def search(company_id: int, query: str, top_k: int = 5) -> list[str]:
    return [c.text for c in search_chunks(company_id, query, top_k)]


def search_chunks(company_id: int, query: str, top_k: int = 5, as_of: int | None = None) -> list[Chunk]:
    """as_of(YYYYMMDD)를 주면 그날 이전에 시행된 문서와 시행일 미상 문서에서만 찾는다.
    시행일 메타데이터가 아예 없는 예전 청크는 as_of 검색에서 빠진다 → 문서 관리에서 시행일을 입력하면 포함된다."""
    collection = get_collection(company_id)
    query_embedding = embed([query])[0]
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas"],
        where={"effective_date": {"$lte": as_of}} if as_of is not None else None,
    )
    if not results["documents"]:
        return []
    return [Chunk(text, (meta or {}).get("source", "unknown"), (meta or {}).get("effective_date", UNKNOWN))
            for text, meta in zip(results["documents"][0], results["metadatas"][0])]
