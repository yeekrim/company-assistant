from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.security import decode_token
from app.models.db_models import User
from app.models.schemas import EffectiveDateRequest
from app.rag.dates import parse_effective_date
from app.services.document_service import process_upload
from app.rag.retriever import list_documents, delete_document, set_effective_date
from app.tables.store import delete_tables
import logging

logger = logging.getLogger(__name__)
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

router = APIRouter(prefix="/api/documents", tags=["documents"])
bearer = HTTPBearer()

async def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    try:
        payload = decode_token(creds.credentials)
        user_id = int(payload["sub"])
    except Exception:
        raise HTTPException(status_code=401, detail="인증이 필요합니다.")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="사용자를 찾을 수 없습니다.")
    return user

def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="관리자만 접근할 수 있습니다.")
    return current_user

@router.post("/upload")
async def upload_documents(
    files: List[UploadFile] = File(...),
    effective_dates: List[str] = Form(default=[]),  # files와 같은 순서의 시행일(YYYY-MM-DD). 비우면 미상
    current_user: User = Depends(require_admin),
):
    if effective_dates and len(effective_dates) != len(files):
        raise HTTPException(status_code=422, detail="시행일 개수가 파일 개수와 다릅니다.")
    results = []
    errors = []
    for i, file in enumerate(files):
        try:
            effective_date = parse_effective_date(effective_dates[i] if effective_dates else None)
            result = await process_upload(file, current_user.company_id, effective_date)
            results.append({"file": file.filename, **result})
        except ValueError as e:
            errors.append({"file": file.filename, "error": str(e)})
    return {"uploaded": results, "errors": errors}

@router.get("")
async def get_documents(current_user: User = Depends(require_admin)):
    docs = list_documents(current_user.company_id)
    return {"documents": docs}

@router.patch("/{doc_name}")
async def update_effective_date(
    doc_name: str,
    data: EffectiveDateRequest,
    current_user: User = Depends(require_admin),
):
    try:
        effective_date = parse_effective_date(data.effective_date)
        set_effective_date(current_user.company_id, doc_name, effective_date)
    except ValueError as e:
        raise HTTPException(status_code=404 if "찾을 수 없습니다" in str(e) else 422, detail=str(e))
    return {"name": doc_name, "effective_date": effective_date}

@router.delete("/{doc_name}")
async def remove_document(
    doc_name: str,
    current_user: User = Depends(require_admin),
):
    try:
        delete_document(current_user.company_id, doc_name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    try:
        delete_tables(current_user.company_id, doc_name)
    except Exception:
        logger.exception("표 삭제 실패: company=%s doc=%s", current_user.company_id, doc_name)
    return {"message": f"'{doc_name}' 삭제 완료"}
