"""hybrid: current를 기본으로 두고, 표 계산만 run_sql 도구로 붙인 방식.

- 검색은 current처럼 질문당 한 번만 한다 (search_documents 도구 없음 → 검색 반복 비용 제거)
- 작은 표는 텍스트로 검색 인덱스에도 넣는다 (답이 표 안에만 있는 질문 대응, kaizen-go r09)
- 큰 표는 인덱스에 요약 한 줄만 넣는다 (표 행이 규정 검색을 밀어내는 문제 방지, current t01)
- 모든 표는 DuckDB에 넣고, 모델은 계산이 필요할 때만 run_sql을 호출한다
"""
import json
import time

import duckdb

from app.rag.chunker import chunk_text
from app.rag.generator import build_prompt

import common
from common import ROOT, DocIndex, Trace, chat
from tables import extract_many
from variants import kaizen_go

DB_PATH = ROOT / "data" / "hybrid.duckdb"
SMALL_ROWS = 30  # 이 행 수 이하의 표는 텍스트로도 인덱싱 (임의 기준, 측정 필요)
MAX_ROUNDS = 3
TOOLS = [t for t in kaizen_go.TOOLS if t["function"]["name"] == "run_sql"]

_con = None
_schema = ""
_index: DocIndex | None = None


def _table_text(tb) -> str:
    """헤더 행도 그대로 남겨, 헤더 판정이 틀린 표(첫 행이 데이터)도 내용이 빠지지 않게 한다."""
    lines = [f"[표] {tb.title}", "| " + " | ".join(tb.columns) + " |"]
    lines += ["| " + " | ".join("" if v is None else str(v) for v in r) + " |" for r in tb.rows]
    return "\n".join(lines)


def _prepare(trace: Trace):
    """업로드 시점에 해당: 표 → DuckDB, 본문 + (작은 표 텍스트 | 큰 표 요약) → 벡터 인덱스."""
    global _con, _schema, _index
    if _con is not None:
        return
    t = time.perf_counter()
    body, tables = extract_many(common.DOCS)
    DB_PATH.unlink(missing_ok=True)
    w = duckdb.connect(str(DB_PATH))
    schema, extra = [], []
    for i, tb in enumerate(tables, 1):
        name = f"t{i}"
        cols = ", ".join(f'"{c}" {kaizen_go._duck_type(tb, j)}' for j, c in enumerate(tb.columns))
        w.execute(f"CREATE TABLE {name} ({cols})")
        w.executemany(f"INSERT INTO {name} VALUES ({', '.join(['?'] * len(tb.columns))})", tb.rows)
        sample = json.dumps([dict(zip(tb.columns, r)) for r in tb.rows[:3]], ensure_ascii=False, default=str)
        schema.append(f"- {name}: {tb.title} ({len(tb.rows)}행)\n  컬럼: {cols}\n  예시: {sample}")
        if len(tb.rows) <= SMALL_ROWS:
            extra += chunk_text(_table_text(tb))
        else:
            extra.append(f"[표 {name}] {tb.title} — 컬럼: {', '.join(tb.columns)} ({len(tb.rows)}행, run_sql로 조회)")
    w.close()
    _con = duckdb.connect(str(DB_PATH), read_only=True)
    _schema = "\n".join(schema)
    _index = DocIndex(chunk_text(body) + extra)
    trace.add_time("prepare", time.perf_counter() - t)


def _system() -> str:
    base = "당신은 사내 문서 기반 AI 어시스턴트입니다. 문서에 있는 내용만 답변하고, 한국어로만 답하세요."
    if not _schema:
        return base
    return f"""{base}

사용 가능한 표(DuckDB):
{_schema}

규칙:
- [문서 내용]에 답이 그대로 있으면 도구 없이 바로 답하세요.
- 합계·평균·개수·최대/최소·순위처럼 표의 여러 행을 계산해야 하면, [문서 내용]에 일부 행이 보이더라도 직접 계산하지 말고 반드시 run_sql을 호출하세요.
- 규정의 기준값(예: 상한 금액)이 [문서 내용]에 있으면 그 값을 SQL 조건에 쓰세요.
- 최종 답변의 숫자는 도구 결과 값을 그대로 쓰고, 금액은 천 단위 쉼표와 '원'을 붙이세요."""


def _run_sql(sql: str, trace: Trace) -> dict:
    """kaizen-go의 검사·타임아웃 로직을 이 방식의 DB 연결로 실행한다."""
    prev = kaizen_go._con
    kaizen_go._con = _con
    try:
        return kaizen_go.run_sql(sql, trace)
    finally:
        kaizen_go._con = prev


async def answer(question: str, index: DocIndex, trace: Trace) -> str:
    """index(앱 방식 인덱스)는 쓰지 않고, 표 크기별로 정리한 자체 인덱스(_index)를 쓴다."""
    _prepare(trace)
    chunks = _index.search(question, top_k=10, trace=trace)
    messages = [{"role": "system", "content": _system()},
                {"role": "user", "content": build_prompt(question, chunks)}]
    kw = {"tools": TOOLS} if _schema else {}
    for _ in range(MAX_ROUNDS):
        msg = await chat(trace, messages, **kw)
        if not msg.tool_calls:
            return msg.content or ""
        messages.append(msg.model_dump(exclude_none=True))
        for call in msg.tool_calls:
            try:
                args = json.loads(call.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            if call.function.name == "run_sql":
                out = _run_sql(args.get("sql", ""), trace)
            else:
                out = {"error": f"알 수 없는 도구: {call.function.name}"}
            trace.tool_log.append({"tool": call.function.name, "args": args, "error": out.get("error")})
            messages.append({"role": "tool", "tool_call_id": call.id,
                             "content": json.dumps(out, ensure_ascii=False, default=str)})
    msg = await chat(trace, messages + [{"role": "user", "content": "지금까지의 도구 결과만으로 최종 답변을 하세요."}])
    return msg.content or ""
