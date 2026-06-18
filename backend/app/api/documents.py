from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.security import decode_token
from app.models.db_models import User
from app.services.document_service import process_upload
from app.rag.retriever import list_documents, delete_document
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
    current_user: User = Depends(require_admin),
):
    results = []
    errors = []
    for file in files:
        try:
            result = await process_upload(file, current_user.company_id)
            results.append({"file": file.filename, **result})
        except ValueError as e:
            errors.append({"file": file.filename, "error": str(e)})
    return {"uploaded": results, "errors": errors}

@router.get("")
async def get_documents(current_user: User = Depends(require_admin)):
    docs = list_documents(current_user.company_id)
    return {"documents": docs}

@router.delete("/{doc_name}")
async def remove_document(
    doc_name: str,
    current_user: User = Depends(require_admin),
):
    try:
        delete_document(current_user.company_id, doc_name)
        return {"message": f"'{doc_name}' 삭제 완료"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
