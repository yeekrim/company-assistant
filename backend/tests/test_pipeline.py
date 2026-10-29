"""pipeline이 시점을 검색에 넘기고, 조각 앞에 문서명·시행일을 붙이는지 확인 (검색·LLM은 가짜)."""
import asyncio
from datetime import date

from app.rag import pipeline
from app.rag.generator import build_prompt, date_rules
from app.rag.retriever import Chunk


def run_with_fakes(monkeypatch, query):
    seen = {}

    def fake_search(company_id, q, top_k, as_of):
        seen["as_of"] = as_of
        return [Chunk("연차는 15일", "복무_2016.pdf", 20160101), Chunk("기타", "기타.pdf", 0)]

    async def fake_generate(q, context, history, rules):
        seen["context"], seen["rules"] = context, rules
        return "답"

    monkeypatch.setattr(pipeline, "search_chunks", fake_search)
    monkeypatch.setattr(pipeline, "generate", fake_generate)
    asyncio.run(pipeline.run(1, query))
    return seen


def test_dated_question_filters_and_states_basis(monkeypatch):
    seen = run_with_fakes(monkeypatch, "2016년에는 연차가 며칠이야?")
    assert seen["as_of"] == 20161231
    assert seen["context"][0] == "[문서: 복무_2016.pdf · 시행일 2016-01-01]\n연차는 15일"
    assert seen["context"][1].startswith("[문서: 기타.pdf · 시행일 미상]")
    assert "기준일은 2016-12-31(질문에 적힌 시점)" in seen["rules"]


def test_undated_question_uses_today(monkeypatch):
    seen = run_with_fakes(monkeypatch, "연차가 며칠이야?")
    assert seen["as_of"] is None
    assert f"기준일은 {date.today().isoformat()}(오늘)" in seen["rules"]


def test_build_prompt_without_rules_is_unchanged_shape():
    p = build_prompt("질문", ["조각"])
    assert "시행일" not in p
    assert "시행일이 가장 늦은 문서" in build_prompt("질문", ["조각"], date_rules("2024-01-01", False))
