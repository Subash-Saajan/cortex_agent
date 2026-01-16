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

    from ..agent.graph import run_agent
    from ..services.memory_service import MemoryService
    import os

    api_key = os.getenv("GOOGLE_API_KEY")
    user_id = chat_request.user_id
    message = chat_request.message

    # Get memory context
    memory_context = await MemoryService.get_memory_context(user_id, db)

    # Check if we need to fetch email/calendar
    message_lower = message.lower()
    needs_email_or_calendar = any(w in message_lower for w in [
        "email", "mail", "inbox", "calendar", "meeting", "schedule", 
        "event", "latest email", "recent email", "upcoming"
    ])

    email_context = ""
    calendar_context = ""

    if needs_email_or_calendar:
        from ..services.gmail_service import GmailService
        from ..services.calendar_service import CalendarService

        try:
            emails = await GmailService.get_inbox(user_id, db, max_results=5)
            if emails:
                email_context = "RECENT EMAILS:\n" + "\n".join([
                    f"- {e['subject']} from {e['from']}\n  {e['preview']}" for e in emails[:5]
                ])
        except Exception as e:
            email_context = f"Could not fetch emails: {str(e)}"

        try:
            events = await CalendarService.get_events(user_id, db, days_ahead=7)
            if events:
                calendar_context = "UPCOMING EVENTS:\n" + "\n".join([
                    f"- {e.get('summary', 'Event')}: {e.get('start', 'TBD')}" for e in events[:5]
                ])
        except Exception as e:
            calendar_context = f"Could not fetch calendar: {str(e)}"

    # Check if we need to update memory (user stating preferences/constraints)
    needs_memory_update = any(w in message_lower for w in [
        "i prefer", "i don't like", "i hate", "i like", "remember",
        "always", "never", "i want", "i need", "make sure",
        "important", "don't forget", "keep in mind"
    ])

    if needs_memory_update:
        await MemoryService.extract_facts(user_id, message, db, source="chat")
        memory_context = await MemoryService.get_memory_context(user_id, db)

    # Build the prompt
    system_prompt = f"""You are Cortex, a personal AI Chief of Staff assistant.

Your capabilities:
1. Answer questions about emails and calendar
2. Draft and send emails based on user requests  
3. Remember user preferences, constraints, and important context
4. Help manage the user's day and projects

Available memory about the user:
{memory_context}

Email context (if any):
{email_context if email_context else "Not asked about email."}

Calendar context (if any):
{calendar_context if calendar_context else "Not asked about calendar."}

Guidelines:
- Be concise and helpful
- If asked about emails, use the provided email context
- If asked about calendar, use the provided calendar context
- Remember important constraints and preferences the user mentions"""

    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain_core.messages import HumanMessage, SystemMessage

    try:
        llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=api_key)
        response = await llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=message)
        ])

        # After responding, extract any new facts from this conversation
        await MemoryService.extract_facts(user_id, message, db, source="chat")

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
