from pydantic import BaseModel, EmailStr
from datetime import datetime

class LoginRequest(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserResponse"

class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    role: str
    company_id: int
    company_name: str

class MessageResponse(BaseModel):
    id: int
    role: str
    content: str
    created_at: datetime

class ConversationResponse(BaseModel):
    id: int
    title: str
    created_at: datetime

class ChatRequest(BaseModel):
    conversation_id: int | None = None
    message: str

class SourceChunk(BaseModel):
    source: str
    effective_date: str  # YYYY-MM-DD 또는 '미상'
    text: str

class ChatResponse(BaseModel):
    id: str
    role: str
    content: str
    created_at: str
    conversation_id: str
    sources: list[SourceChunk] = []

class EffectiveDateRequest(BaseModel):
    effective_date: str | None = None  # YYYY-MM-DD, 비우면 미상
