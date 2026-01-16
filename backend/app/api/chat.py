from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import List
from langchain_core.messages import HumanMessage, AIMessage
from slowapi import Limiter
from slowapi.util import get_remote_address
from ..db.database import get_db
from ..db.models import User, ChatMessage
from ..services.memory_service import MemoryService
import uuid

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

class ChatRequest(BaseModel):
    message: str
    user_id: str

class ChatResponse(BaseModel):
    response: str
    user_id: str

class MessageHistory(BaseModel):
    role: str
    content: str

async def get_or_create_user(user_id: str, db: AsyncSession) -> User:
    """Get or create user"""
    from sqlalchemy import select

    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        user_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, user_id)

    stmt = select(User).where(User.id == user_uuid)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        user = User(id=user_uuid, email=f"user-{user_id}@cortex.ai")
        db.add(user)
        await db.commit()

    return user

@router.post("/chat", response_model=ChatResponse)
@limiter.limit("10/minute")
async def chat(request: Request, chat_request: ChatRequest, db: AsyncSession = Depends(get_db)):
    """Chat endpoint using the intelligent LangGraph agent"""

    from ..agent.graph import run_agent
    from ..db.models import ChatMessage
    import uuid

    user_id = chat_request.user_id
    message = chat_request.message

    try:
        # 1. Run the intelligent agent
        response_text = await run_agent(user_id, message, db)

        # 2. Store messages in history
        try:
            user_uuid = uuid.UUID(user_id)
        except ValueError:
            user_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, user_id)

        user_msg = ChatMessage(user_id=user_uuid, role="user", content=message)
        ai_msg = ChatMessage(user_id=user_uuid, role="assistant", content=response_text)
        
        db.add(user_msg)
        db.add(ai_msg)
        await db.commit()

        return ChatResponse(response=response_text, user_id=user_id)
        
    except Exception as e:
        import traceback
        print(f"Agent Error: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Agent Error: {str(e)}")

@router.get("/chat/history/{user_id}")
@limiter.limit("30/minute")  # 30 requests per minute per IP
async def get_chat_history(request: Request, user_id: str, db: AsyncSession = Depends(get_db)):
    """Get chat history for user - Rate limited"""
    from sqlalchemy import select

    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        user_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, user_id)

    stmt = select(ChatMessage).where(ChatMessage.user_id == user_uuid).order_by(ChatMessage.created_at)
    result = await db.execute(stmt)
    messages = result.scalars().all()

    return [
        MessageHistory(role=msg.role, content=msg.content)
        for msg in messages
    ]
