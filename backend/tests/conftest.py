"""테스트 공통 설정. pytest가 테스트 파일보다 먼저 읽는다.

앱 설정(app/core/config.py)은 DATABASE_URL·SECRET_KEY를 필수로 요구한다.
테스트는 실제 DB·LLM에 접속하지 않으므로(모두 가짜로 대체) 값의 존재만 필요하다.
.env가 없는 환경(CI, 새로 클론한 저장소)에서도 테스트가 돌도록 더미 값을 넣는다.
"""
import os

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
