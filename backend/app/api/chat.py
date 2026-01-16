from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import List
from langchain_core.messages import HumanMessage, AIMessage
from slowapi import Limiter
from slowapi.util import get_remote_address
from ..db.database import get_db
from ..db.models import User, ChatMessage
from ..agent.graph import agent
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
@limiter.limit("10/minute")  # 10 requests per minute per IP
async def chat(request: Request, chat_request: ChatRequest, db: AsyncSession = Depends(get_db)):
    """Chat endpoint with agent and memory - Rate limited to prevent abuse"""

    # Get or create user
    user = await get_or_create_user(chat_request.user_id, db)

    # Get memory context
    memory_context = await MemoryService.get_memory_context(chat_request.user_id, db)

    # Get recent chat history
    from sqlalchemy import select
    stmt = select(ChatMessage).where(ChatMessage.user_id == user.id).order_by(ChatMessage.created_at.desc()).limit(10)
    result = await db.execute(stmt)
    messages = reversed(result.scalars().all())

    # Build message list for agent
    message_list = [
        HumanMessage(content=msg.content) if msg.role == "user" else AIMessage(content=msg.content)
        for msg in messages
    ]
    message_list.append(HumanMessage(content=chat_request.message))

    # Process with agent
    state = {
        "user_id": chat_request.user_id,
        "messages": message_list,
        "memory_context": memory_context,
        "response": ""
    }

    result_state = agent.invoke(state)
    response = result_state["response"]

    # Store message in database
    user_msg = ChatMessage(user_id=user.id, role="user", content=chat_request.message)
    assistant_msg = ChatMessage(user_id=user.id, role="assistant", content=response)

    db.add(user_msg)
    db.add(assistant_msg)
    await db.commit()

    # Extract and store facts from user message
    facts = await MemoryService.extract_facts(chat_request.user_id, chat_request.message, db)
    for fact in facts:
        await MemoryService.store_fact(
            chat_request.user_id,
            fact["fact"],
            fact.get("category", "other"),
            db
        )

    return ChatResponse(response=response, user_id=chat_request.user_id)

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
