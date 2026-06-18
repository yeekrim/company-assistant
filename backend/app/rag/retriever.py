import chromadb
from app.core.config import settings
from app.rag.embedder import embed

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

def add_documents(company_id: int, chunks: list[str], doc_name: str):
    collection = get_collection(company_id)
    embeddings = embed(chunks)
    ids = [f"{doc_name}_{i}" for i in range(len(chunks))]
    collection.upsert(
        ids=ids,
        embeddings=embeddings,
        documents=chunks,
        metadatas=[{"source": doc_name} for _ in chunks],
    )

def list_documents(company_id: int) -> list[dict]:
    collection = get_collection(company_id)
    result = collection.get(include=["metadatas"])
    seen = {}
    for meta in result["metadatas"]:
        src = meta.get("source", "unknown")
        seen[src] = seen.get(src, 0) + 1
    return [{"name": name, "chunks": count} for name, count in seen.items()]

def delete_document(company_id: int, doc_name: str):
    collection = get_collection(company_id)
    result = collection.get(where={"source": doc_name}, include=["metadatas"])
    if not result["ids"]:
        raise ValueError(f"'{doc_name}' 문서를 찾을 수 없습니다.")
    collection.delete(ids=result["ids"])

def search(company_id: int, query: str, top_k: int = 5) -> list[str]:
    collection = get_collection(company_id)
    query_embedding = embed([query])[0]
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents"],
    )
    return results["documents"][0] if results["documents"] else []
