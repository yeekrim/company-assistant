from datetime import date

import duckdb
import pytest

from app.core.config import settings
from app.tables import store
from app.tables.extractor import ExtractedTable


@pytest.fixture(autouse=True)
def tmp_store(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "TABLE_STORE_DIR", str(tmp_path))


def expenses(n=3):
    return ExtractedTable(
        title="경비 내역",
        columns=["이름", "사용일", "금액"],
        rows=[[f"직원{i}", date(2026, 1, i + 1), 1000 * (i + 1)] for i in range(n)],
    )


def query(company_id, sql):
    with duckdb.connect(str(store.db_path(company_id)), read_only=True) as con:
        return con.execute(sql).fetchall()


def test_save_and_list():
    saved = store.save_tables(1, "경비.pdf", [expenses()])
    [t] = store.list_tables(1)
    assert t["table_name"] == saved[0]["table_name"]
    assert t["doc_name"] == "경비.pdf"
    assert t["row_count"] == 3
    assert [c["type"] for c in t["columns"]] == ["VARCHAR", "DATE", "BIGINT"]


def test_saved_table_is_queryable_with_korean_columns():
    [t] = store.save_tables(1, "경비.pdf", [expenses()])
    assert query(1, f'SELECT SUM("금액") FROM {t["table_name"]}') == [(6000,)]


def test_reupload_replaces_tables():
    store.save_tables(1, "경비.pdf", [expenses(3), expenses(2)])
    store.save_tables(1, "경비.pdf", [expenses(5)])
    [t] = store.list_tables(1)
    assert t["row_count"] == 5
    assert len(query(1, "SELECT table_name FROM information_schema.tables WHERE table_name LIKE 't_%'")) == 1


def test_reupload_without_tables_removes_old_ones():
    store.save_tables(1, "경비.pdf", [expenses()])
    store.save_tables(1, "경비.pdf", [])
    assert store.list_tables(1) == []


def test_delete_only_target_document():
    store.save_tables(1, "a.pdf", [expenses()])
    store.save_tables(1, "b.pdf", [expenses()])
    assert store.delete_tables(1, "a.pdf") == 1
    assert [t["doc_name"] for t in store.list_tables(1)] == ["b.pdf"]


def test_companies_are_isolated():
    store.save_tables(1, "경비.pdf", [expenses()])
    assert store.list_tables(2) == []
    assert store.db_path(1) != store.db_path(2)


def test_delete_and_list_without_db_file():
    assert store.delete_tables(99, "없음.pdf") == 0
    assert store.list_tables(99) == []


def test_failed_save_rolls_back():
    store.save_tables(1, "경비.pdf", [expenses()])
    broken = ExtractedTable(title="깨진 표", columns=["a"], rows=[[1, 2]])  # 열 개수 불일치
    with pytest.raises(Exception):
        store.save_tables(1, "경비.pdf", [broken])
    [t] = store.list_tables(1)  # 기존 표가 그대로 남아 있어야 함
    assert t["row_count"] == 3
