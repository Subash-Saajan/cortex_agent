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
@limiter.limit("10/minute")
async def chat(request: Request, chat_request: ChatRequest, db: AsyncSession = Depends(get_db)):
    """Chat endpoint with agent, memory, email, and calendar - Rate limited"""

    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain_core.messages import HumanMessage
    import os

    api_key = os.getenv("GOOGLE_API_KEY")
    user_id = chat_request.user_id
    message = chat_request.message.lower()

    # Check if user is asking about email or calendar
    is_email_query = any(word in message for word in ['email', 'mail', 'inbox', 'message', 'latest email', 'recent email', 'unread'])
    is_calendar_query = any(word in message for word in ['calendar', 'event', 'meeting', 'schedule', 'appointment'])

    # Build context
    context_parts = []

    # Add email context if relevant
    if is_email_query:
        try:
            from ..services.gmail_service import GmailService
            emails = await GmailService.get_inbox(user_id, db, max_results=5)
            if emails:
                email_text = "RECENT EMAILS:\n"
                for email in emails[:5]:
                    email_text += f"- {email['subject']} from {email['from']}\n  {email['preview']}\n\n"
                context_parts.append(email_text)
        except Exception as e:
            context_parts.append(f"Note: Could not fetch emails: {str(e)}\n")

    # Add calendar context if relevant
    if is_calendar_query:
        try:
            from ..services.calendar_service import CalendarService
            events = await CalendarService.get_events(user_id, db, days_ahead=7)
            if events:
                event_text = "UPCOMING CALENDAR EVENTS:\n"
                for event in events[:5]:
                    event_text += f"- {event['summary']}: {event['start']}\n"
                context_parts.append(event_text)
        except Exception as e:
            context_parts.append(f"Note: Could not fetch calendar: {str(e)}\n")

    # Build the full prompt
    if context_parts:
        full_prompt = "Use the following context to answer the user's question:\n\n"
        full_prompt += "\n".join(context_parts)
        full_prompt += f"\n\nUser's question: {chat_request.message}"
    else:
        full_prompt = chat_request.message

    try:
        llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=api_key)
        response = await llm.ainvoke([HumanMessage(content=full_prompt)])
        return ChatResponse(response=response.content, user_id=user_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM Error: {str(e)}")

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
