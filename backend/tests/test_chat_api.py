"""채팅 API가 답변 생성 실패를 502와 안내 메시지로 돌려주고, 저장을 되돌리는지 확인. (인증·DB·LLM은 가짜로 대체)"""
import pytest
from fastapi.testclient import TestClient

from app.api import chat
from app.core.database import get_db
from app.main import app


class FakeUser:
    id = 1
    company_id = 7
    role = "employee"


class FakeResult:
    def scalars(self):
        return self

    def all(self):
        return []


class FakeSession:
    def __init__(self):
        self.added, self.committed, self.rolled_back = [], False, False

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        for obj in self.added:
            obj.id = obj.id or 1

    async def execute(self, _query):
        return FakeResult()

    async def commit(self):
        self.committed = True

    async def rollback(self):
        self.rolled_back = True


@pytest.fixture
def session():
    s = FakeSession()
    app.dependency_overrides[chat.get_current_user] = lambda: FakeUser()
    app.dependency_overrides[get_db] = lambda: s
    yield s
    app.dependency_overrides.clear()


def test_llm_failure_returns_502_with_message_and_rolls_back(session, monkeypatch):
    async def failing_run(*_args, **_kwargs):
        raise RuntimeError("404 Function not found")

    monkeypatch.setattr(chat, "rag_run", failing_run)
    res = TestClient(app).post("/api/chat", json={"message": "연차는 며칠이야?"})

    assert res.status_code == 502
    assert res.json()["detail"] == "답변을 생성하지 못했습니다. 잠시 후 다시 시도해 주세요."
    assert session.rolled_back and not session.committed
