from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.security import decode_token
from app.models.db_models import User, Conversation, Message
from app.models.schemas import ChatRequest, ChatResponse
from app.rag.pipeline import run as rag_run
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

router = APIRouter(prefix="/api/chat", tags=["chat"])
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

@router.post("", response_model=ChatResponse)
async def chat(
    data: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # 대화 생성 또는 조회
    if data.conversation_id:
        result = await db.execute(
            select(Conversation).where(
                Conversation.id == data.conversation_id,
                Conversation.user_id == current_user.id,
            )
        )
        conversation = result.scalar_one_or_none()
        if not conversation:
            raise HTTPException(status_code=404, detail="대화를 찾을 수 없습니다.")
    else:
        conversation = Conversation(user_id=current_user.id, title=data.message[:30])
        db.add(conversation)
        await db.flush()

    # 사용자 메시지 저장
    user_msg = Message(
        conversation_id=conversation.id,
        role="user",
        content=data.message,
    )
    db.add(user_msg)

    # RAG 파이프라인 실행
    answer = await rag_run(current_user.company_id, data.message)

    # 어시스턴트 메시지 저장
    now = datetime.utcnow()
    assistant_msg = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=answer,
        created_at=now,
    )
    db.add(assistant_msg)
    await db.commit()

    return ChatResponse(
        id=str(assistant_msg.id),
        role="assistant",
        content=answer,
        created_at=now.isoformat(),
        conversation_id=str(conversation.id),
    )
