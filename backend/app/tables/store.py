"""회사별 표 저장소 (회사 1곳 = DuckDB 파일 1개).

업로드 시 문서의 표를 저장하고, 문서 삭제 시 함께 지운다.
모델이 SQL로 조회하는 기능은 다음 단계에서 읽기 전용 연결로 추가한다.
"""
import hashlib
import json
import threading
from datetime import date, datetime
from pathlib import Path

import duckdb

from app.core.config import settings
from app.tables.extractor import ExtractedTable

REGISTRY_DDL = """
CREATE TABLE IF NOT EXISTS _tables (
    table_name VARCHAR PRIMARY KEY,
    doc_name   VARCHAR NOT NULL,
    title      VARCHAR,
    columns    VARCHAR,   -- JSON: [{"name": ..., "type": ...}]
    row_count  INTEGER,
    created_at TIMESTAMP
)
"""

# DuckDB 파일은 한 프로세스에서 동시에 한 연결만 쓰도록 회사별 잠금
_locks: dict[int, threading.Lock] = {}
_locks_guard = threading.Lock()


def _lock(company_id: int) -> threading.Lock:
    with _locks_guard:
        return _locks.setdefault(company_id, threading.Lock())


def db_path(company_id: int) -> Path:
    d = Path(settings.TABLE_STORE_DIR)
    d.mkdir(parents=True, exist_ok=True)
    return d / f"company_{company_id}.duckdb"


def _table_name(doc_name: str, index: int) -> str:
    # 파일명에 한글·공백·특수문자가 있어도 안전한 식별자가 되도록 해시 사용
    return f"t_{hashlib.sha1(doc_name.encode()).hexdigest()[:10]}_{index}"


def _quote(ident: str) -> str:
    return '"' + ident.replace('"', '""') + '"'


def _duck_type(values: list) -> str:
    vals = [v for v in values if v is not None]
    if vals and all(isinstance(v, int) for v in vals):
        return "BIGINT"
    if vals and all(isinstance(v, (int, float)) for v in vals):
        return "DOUBLE"
    if vals and all(isinstance(v, date) for v in vals):
        return "DATE"
    return "VARCHAR"


def _delete(con: duckdb.DuckDBPyConnection, doc_name: str) -> int:
    names = [r[0] for r in con.execute(
        "SELECT table_name FROM _tables WHERE doc_name = ?", [doc_name]).fetchall()]
    for name in names:
        con.execute(f"DROP TABLE IF EXISTS {name}")
    con.execute("DELETE FROM _tables WHERE doc_name = ?", [doc_name])
    return len(names)


def save_tables(company_id: int, doc_name: str, tables: list[ExtractedTable]) -> list[dict]:
    """문서의 표를 저장한다. 같은 문서의 기존 표는 먼저 지운다 (재업로드 대응)."""
    saved = []
    with _lock(company_id), duckdb.connect(str(db_path(company_id))) as con:
        con.execute(REGISTRY_DDL)
        con.begin()
        try:
            _delete(con, doc_name)
            for i, t in enumerate(tables, 1):
                name = _table_name(doc_name, i)
                types = [_duck_type([r[j] for r in t.rows]) for j in range(len(t.columns))]
                cols_sql = ", ".join(f"{_quote(c)} {ty}" for c, ty in zip(t.columns, types))
                con.execute(f"CREATE TABLE {name} ({cols_sql})")
                if t.rows:
                    placeholders = ", ".join(["?"] * len(t.columns))
                    con.executemany(f"INSERT INTO {name} VALUES ({placeholders})", t.rows)
                columns = [{"name": c, "type": ty} for c, ty in zip(t.columns, types)]
                con.execute(
                    "INSERT INTO _tables VALUES (?, ?, ?, ?, ?, ?)",
                    [name, doc_name, t.title, json.dumps(columns, ensure_ascii=False),
                     len(t.rows), datetime.utcnow()],
                )
                saved.append({"table_name": name, "title": t.title, "columns": columns,
                              "row_count": len(t.rows)})
            con.commit()
        except Exception:
            con.rollback()
            raise
    return saved


def delete_tables(company_id: int, doc_name: str) -> int:
    path = db_path(company_id)
    if not path.exists():
        return 0
    with _lock(company_id), duckdb.connect(str(path)) as con:
        con.execute(REGISTRY_DDL)
        con.begin()
        try:
            n = _delete(con, doc_name)
            con.commit()
        except Exception:
            con.rollback()
            raise
    return n


def list_tables(company_id: int) -> list[dict]:
    path = db_path(company_id)
    if not path.exists():
        return []
    with _lock(company_id), duckdb.connect(str(path)) as con:
        con.execute(REGISTRY_DDL)
        rows = con.execute(
            "SELECT table_name, doc_name, title, columns, row_count FROM _tables ORDER BY doc_name, table_name"
        ).fetchall()
    return [{"table_name": r[0], "doc_name": r[1], "title": r[2], "columns": json.loads(r[3]),
             "row_count": r[4]} for r in rows]
