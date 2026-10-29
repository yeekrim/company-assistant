from datetime import date

from app.rag.dates import format_date, query_as_of, to_int
from app.rag.retriever import search_chunks
from app.rag.generator import date_rules, generate

async def run(company_id: int, query: str, history: list[dict] | None = None) -> str:
    # 질문에 시점이 있으면 그때 시행 중이던 문서에서만 찾고, 없으면 오늘 기준으로 최신 문서를 따르게 한다
    as_of = query_as_of(query)
    chunks = search_chunks(company_id, query, top_k=10, as_of=as_of)
    context = [f"[문서: {c.source} · 시행일 {format_date(c.effective_date)}]\n{c.text}" for c in chunks]
    rules = date_rules(format_date(as_of or to_int(date.today())), from_query=as_of is not None)
    return await generate(query, context, history or [], rules)
