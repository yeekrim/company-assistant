import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.core.database import get_db
from app.core.security import decode_token
from app.models.db_models import User, Conversation, Message
from app.models.schemas import ChatRequest, ChatResponse
from app.rag.dates import format_date
from app.rag.pipeline import run as rag_run
from app.rag.embedder import embed
import numpy as np
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

logger = logging.getLogger(__name__)

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
        {"id": str(m.id), "role": m.role, "content": m.content, "created_at": m.created_at.isoformat(),
         "sources": m.sources or []}
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

    # 이전 대화 최근 6턴 조회 후 현재 질문과 유사도 기반 필터링
    history_result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation.id)
        .order_by(Message.created_at.desc())
        .limit(6)
    )
    recent_messages = list(reversed(history_result.scalars().all()))

    history = []
    if recent_messages:
        query_vec = np.array(embed([data.message])[0])
        for m in recent_messages:
            msg_vec = np.array(embed([m.content])[0])
            cosine_sim = float(np.dot(query_vec, msg_vec) / (np.linalg.norm(query_vec) * np.linalg.norm(msg_vec)))
            if cosine_sim >= 0.7:
                history.append({"role": m.role, "content": m.content})

    user_time = datetime.utcnow()
    user_msg = Message(
        conversation_id=conversation.id,
        role="user",
        content=data.message,
        created_at=user_time,
    )
    db.add(user_msg)

    conversation_id = conversation.id
    try:
        answer, chunks = await rag_run(current_user.company_id, data.message, history)
    except Exception:
        # LLM 오류(모델 종료·게이트웨이 오류)나 네트워크 오류. 질문만 남은 대화가 생기지 않게 저장을 되돌린다
        logger.exception("답변 생성 실패: company=%s conversation=%s", current_user.company_id, conversation_id)
        await db.rollback()
        raise HTTPException(status_code=502, detail="답변을 생성하지 못했습니다. 잠시 후 다시 시도해 주세요.")
    sources = [{"source": c.source, "effective_date": format_date(c.effective_date), "text": c.text} for c in chunks]

    assistant_msg = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=answer,
        sources=sources,
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
        sources=sources,
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
