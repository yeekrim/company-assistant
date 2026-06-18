import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.core.config import settings
from app.core.security import hash_password
from app.models.db_models import Base, Company, User

engine = create_async_engine(settings.DATABASE_URL)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

DEFAULT_PASSWORD = "pass1234"

COMPANIES = [
    {
        "name": "버추얼코리아",
        "email_domain": "virtual.co.kr",
        "employee_id_prefix": "018",
        "employee_id_length": 9,
        "users": [
            {"name": "이경림", "employee_id": "admin", "role": "admin"},
            {"name": "이서연", "employee_id": "018100002", "role": "employee"},
            {"name": "박지호", "employee_id": "018100003", "role": "employee"},
            {"name": "최유나", "employee_id": "018100004", "role": "employee"},
            {"name": "정도윤", "employee_id": "018100005", "role": "employee"},
        ],
    },
    {
        "name": "레포컴퍼니",
        "email_domain": "repo.com",
        "employee_id_prefix": "102",
        "employee_id_length": 10,
        "users": [
            {"name": "한소희", "employee_id": "1021000001", "role": "admin"},
            {"name": "오태양", "employee_id": "1021000002", "role": "employee"},
            {"name": "신예린", "employee_id": "1021000003", "role": "employee"},
            {"name": "윤재원", "employee_id": "1021000004", "role": "employee"},
            {"name": "임하늘", "employee_id": "1021000005", "role": "employee"},
        ],
    },
]

async def seed():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        for company_data in COMPANIES:
            company = Company(
                name=company_data["name"],
                email_domain=company_data["email_domain"],
                employee_id_prefix=company_data["employee_id_prefix"],
                employee_id_length=company_data["employee_id_length"],
            )
            session.add(company)
            await session.flush()

            print(f"\n🏢 {company.name} ({company.email_domain})")
            for u in company_data["users"]:
                email = f"{u['employee_id']}@{company_data['email_domain']}"
                user = User(
                    company_id=company.id,
                    email=email,
                    name=u["name"],
                    hashed_password=hash_password(DEFAULT_PASSWORD),
                    role=u["role"],
                )
                session.add(user)
                tag = "👑 admin" if u["role"] == "admin" else "   사원"
                print(f"  {tag} | {u['name']} | {email}")

        await session.commit()
        print(f"\n✅ 시딩 완료 (기본 비밀번호: {DEFAULT_PASSWORD})")

asyncio.run(seed())
