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
from collections import deque
import os

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

MAX_CONVERSATION_LENGTH = 10

conversation_histories = {}

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
async def chat(request: Request, chat_request: ChatRequest, db: AsyncSession = Depends(get_db)):
    """Chat endpoint using the intelligent LangGraph agent with conversation memory"""

    from ..agent.graph import run_agent
    from ..db.models import ChatMessage
    import uuid

    user_id = chat_request.user_id
    message = chat_request.message

    if user_id not in conversation_histories:
        conversation_histories[user_id] = deque(maxlen=MAX_CONVERSATION_LENGTH)

    conversation_histories[user_id].append({"role": "user", "content": message})

    try:
        response_text = await run_agent(user_id, message, db, list(conversation_histories[user_id]))

        conversation_histories[user_id].append({"role": "assistant", "content": response_text})

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
        import google.generativeai as genai
        
        print(f"Agent Error: {str(e)}")
        print(traceback.format_exc())
        
        if "404" in str(e) or "not found" in str(e).lower():
            try:
                print("--- DEBUG: CHECKING AVAILABLE MODELS ---")
                api_key = os.getenv("GOOGLE_API_KEY")
                if api_key:
                    genai.configure(api_key=api_key)
                    models = genai.list_models()
                    available_models = []
                    for m in models:
                        model_info = f"{m.name} (Methods: {m.supported_generation_methods})"
                        print(f"Found model: {model_info}")
                        if "generateContent" in m.supported_generation_methods:
                            available_models.append(m.name)
                    print(f"Models supporting generateContent: {available_models}")
                else:
                    print("GOOGLE_API_KEY not found in env")
                print("--- END DEBUG ---")
            except Exception as model_err:
                print(f"Failed to list models: {model_err}")
                
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
