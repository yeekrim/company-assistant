"""kaizen-go (改善後): 개선 후 방식. 모델은 스키마만 보고 SQL을 짜고, 계산은 DuckDB가 한다.

- 표는 읽기 전용 DuckDB 파일에 저장 → 모델이 만든 SQL은 데이터를 바꿀 수 없음
- 결과는 최대 20행만 모델에 보여주고, 전체는 result_id로 참조 (아티팩트용)
- 벡터 인덱스에는 표 행을 넣지 않고 본문 + 표 요약 한 줄씩만 넣음
  (표 행 청크가 규정 본문 검색을 밀어내는 문제 방지)
"""
import json
import re
import threading
import time
import uuid

import duckdb

from app.rag.chunker import chunk_text

from common import PDF_PATH, ROOT, DocIndex, Trace, chat
from tables import extract

DB_PATH = ROOT / "data" / "kaizen_go.duckdb"
MAX_ROUNDS = 4
MAX_ROWS = 20
SQL_TIMEOUT = 3.0

RESULTS: dict[str, dict] = {}  # result_id → 전체 결과 (앱에서는 DB/캐시에 저장할 자리)
_con = None
_schema = None
_index: DocIndex | None = None

TOOLS = [
    {"type": "function", "function": {
        "name": "run_sql",
        "description": "DuckDB에서 SELECT 쿼리를 실행해 결과를 돌려준다. 합계·평균·개수·최대/최소·필터·그룹 등 표 데이터 계산은 반드시 이 도구로 한다.",
        "parameters": {"type": "object", "properties": {
            "sql": {"type": "string", "description": "SELECT 또는 WITH로 시작하는 단일 DuckDB SQL. 한글 컬럼명은 큰따옴표로 감쌀 것."},
        }, "required": ["sql"]},
    }},
    {"type": "function", "function": {
        "name": "search_documents",
        "description": "사내 문서 본문(규정 등)에서 질문과 관련된 부분을 검색한다. 규정·절차·기준 금액 같은 서술형 정보가 필요할 때 사용한다.",
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string"},
        }, "required": ["query"]},
    }},
]


def _build_db() -> tuple[duckdb.DuckDBPyConnection, str, DocIndex]:
    """업로드 시점에 해당: PDF 표 → DuckDB 테이블, 본문 + 표 요약 → 벡터 인덱스."""
    body, tables = extract(str(PDF_PATH))
    DB_PATH.unlink(missing_ok=True)
    w = duckdb.connect(str(DB_PATH))
    lines = []
    for i, tb in enumerate(tables, 1):
        name = f"t{i}"
        cols = ", ".join(f'"{c}" {_duck_type(tb, j)}' for j, c in enumerate(tb.columns))
        w.execute(f"CREATE TABLE {name} ({cols})")
        w.executemany(f"INSERT INTO {name} VALUES ({', '.join(['?'] * len(tb.columns))})", tb.rows)
        sample = json.dumps([dict(zip(tb.columns, r)) for r in tb.rows[:3]], ensure_ascii=False, default=str)
        lines.append(f"- {name}: {tb.title} ({len(tb.rows)}행)\n  컬럼: {cols}\n  예시: {sample}")
    w.close()
    summaries = [f"[표 {i}] {tb.title} — 컬럼: {', '.join(tb.columns)} ({len(tb.rows)}행, run_sql로 조회)"
                 for i, tb in enumerate(tables, 1)]
    index = DocIndex(chunk_text(body) + summaries)
    return duckdb.connect(str(DB_PATH), read_only=True), "\n".join(lines), index


def _duck_type(tb, j) -> str:
    vals = [r[j] for r in tb.rows if r[j] is not None]
    if vals and all(isinstance(v, int) for v in vals):
        return "BIGINT"
    if vals and all(isinstance(v, (int, float)) for v in vals):
        return "DOUBLE"
    if vals and all(hasattr(v, "isoformat") for v in vals):
        return "DATE"
    return "VARCHAR"


def _ensure_db(trace: Trace):
    global _con, _schema, _index
    if _con is None:
        t = time.perf_counter()
        _con, _schema, _index = _build_db()
        trace.add_time("prepare", time.perf_counter() - t)


def run_sql(sql: str, trace: Trace) -> dict:
    sql = sql.strip().rstrip(";").strip()
    if ";" in sql or not re.match(r"(?is)^\s*(select|with)\b", sql):
        return {"error": "SELECT/WITH로 시작하는 단일 쿼리만 허용됩니다."}
    timer = threading.Timer(SQL_TIMEOUT, _con.interrupt)
    t = time.perf_counter()
    timer.start()
    try:
        cur = _con.execute(sql)
        cols = [d[0] for d in cur.description]
        rows = cur.fetchall()
    except Exception as e:
        return {"error": str(e)[:300]}
    finally:
        timer.cancel()
        trace.add_time("sql", time.perf_counter() - t)
    rid = uuid.uuid4().hex[:8]
    RESULTS[rid] = {"sql": sql, "columns": cols, "rows": rows}
    trace.artifacts.append({"result_id": rid, "columns": cols, "row_count": len(rows)})
    return {"result_id": rid, "columns": cols, "row_count": len(rows), "rows": rows[:MAX_ROWS],
            "truncated": len(rows) > MAX_ROWS}


def _system() -> str:
    return f"""당신은 사내 문서 기반 AI 어시스턴트입니다. 한국어로만 답하세요.

사용 가능한 표(DuckDB):
{_schema}

규칙:
- 표 데이터로 계산하거나 조회해야 하는 질문은 반드시 run_sql을 호출하고, 숫자를 직접 계산하지 마세요.
- 규정·기준 등 서술형 정보가 필요하면 search_documents를 호출하세요. (예: 규정상 상한 금액을 확인한 뒤 SQL 조건에 사용)
- 최종 답변의 숫자는 도구 결과 값을 그대로 쓰고, 금액은 천 단위 쉼표와 '원'을 붙이세요.
- 문서와 표에 없는 내용은 추측하지 마세요."""


async def answer(question: str, index: DocIndex, trace: Trace) -> str:
    """index(앱 방식 인덱스)는 쓰지 않고, 표를 뺀 자체 인덱스(_index)를 쓴다."""
    _ensure_db(trace)
    messages = [{"role": "system", "content": _system()}, {"role": "user", "content": question}]
    for _ in range(MAX_ROUNDS):
        msg = await chat(trace, messages, tools=TOOLS)
        if not msg.tool_calls:
            return msg.content or ""
        messages.append(msg.model_dump(exclude_none=True))
        for call in msg.tool_calls:
            try:
                args = json.loads(call.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            if call.function.name == "run_sql":
                out = run_sql(args.get("sql", ""), trace)
            elif call.function.name == "search_documents":
                out = {"chunks": _index.search(args.get("query", question), top_k=5, trace=trace)}
            else:
                out = {"error": f"알 수 없는 도구: {call.function.name}"}
            trace.tool_log.append({"tool": call.function.name, "args": args,
                                   "error": out.get("error") if isinstance(out, dict) else None})
            messages.append({"role": "tool", "tool_call_id": call.id,
                             "content": json.dumps(out, ensure_ascii=False, default=str)})
    # 도구 호출 한도 도달: 도구 없이 지금까지 결과로 답하게 함
    msg = await chat(trace, messages + [{"role": "user", "content": "지금까지의 도구 결과만으로 최종 답변을 하세요."}])
    return msg.content or ""
