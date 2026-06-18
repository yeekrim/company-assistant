import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.core.config import settings
from app.core.security import hash_password
from app.models.db_models import Base, User

engine = create_async_engine(settings.DATABASE_URL)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

USERS = [
    {"email": "madcoder", "name": "개발자", "password": "root123"},
]

async def seed():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        for u in USERS:
            user = User(
                email=u["email"],
                name=u["name"],
                hashed_password=hash_password(u["password"]),
            )
            session.add(user)

        await session.commit()
        print("✅ 시딩 완료")
        for u in USERS:
            print(f"   - {u['email']} / {u['password']}")

asyncio.run(seed())
