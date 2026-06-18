from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
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

@router.get("/conversations")
async def list_conversations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == current_user.id)
        .order_by(Conversation.created_at.desc())
    )
    conversations = result.scalars().all()
    return [
        {"id": str(c.id), "title": c.title, "created_at": c.created_at.isoformat()}
        for c in conversations
    ]

@router.get("/conversations/{conversation_id}/messages")
async def get_messages(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conv_result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id,
        )
    )
    conversation = conv_result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=404, detail="대화를 찾을 수 없습니다.")

    msg_result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
    )
    messages = msg_result.scalars().all()
    return [
        {"id": str(m.id), "role": m.role, "content": m.content, "created_at": m.created_at.isoformat()}
        for m in messages
    ]

@router.post("")
async def chat(
    data: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
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

    user_time = datetime.utcnow()
    user_msg = Message(
        conversation_id=conversation.id,
        role="user",
        content=data.message,
        created_at=user_time,
    )
    db.add(user_msg)

    answer = await rag_run(current_user.company_id, data.message)

    assistant_msg = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=answer,
        created_at=datetime.utcnow(),
    )
    db.add(assistant_msg)
    await db.commit()

    return ChatResponse(
        id=str(assistant_msg.id),
        role="assistant",
        content=answer,
        created_at=assistant_msg.created_at.isoformat(),
        conversation_id=str(conversation.id),
    )

@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id,
        )
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=404, detail="대화를 찾을 수 없습니다.")

    await db.execute(delete(Message).where(Message.conversation_id == conversation_id))
    await db.delete(conversation)
    await db.commit()
    return {"message": "삭제 완료"}
