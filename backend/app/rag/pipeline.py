from app.rag.retriever import search
from app.rag.generator import generate

async def run(company_id: int, query: str) -> str:
    context_chunks = search(company_id, query, top_k=5)
    return await generate(query, context_chunks)
