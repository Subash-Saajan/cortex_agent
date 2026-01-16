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

    from ..services.memory_service import MemoryService
    from ..services.gmail_service import GmailService
    from ..services.calendar_service import CalendarService
    import os

    api_key = os.getenv("GOOGLE_API_KEY")
    user_id = chat_request.user_id
    message = chat_request.message
    message_lower = message.lower()

    # Check if we need to fetch email/calendar
    needs_email = any(w in message_lower for w in ["email", "mail", "inbox", "latest", "recent", "unread", "message"])
    needs_calendar = any(w in message_lower for w in ["meeting", "meet", "calendar", "schedule", "event", "jan ", " feb", " mar", "appointment"])
    needs_memory_update = any(w in message_lower for w in ["prefer", "don't like", "hate", "remember", "always", "never", "important", "vacation", "on vacation", "until"])

    email_context = ""
    calendar_context = ""
    memory_context = ""

    # Fetch context in parallel
    email_task = None
    calendar_task = None
    memory_task = None

    if needs_email or needs_calendar or needs_memory_update:
        if needs_email:
            email_task = GmailService.get_inbox(user_id, db, max_results=5)
        if needs_calendar:
            calendar_task = CalendarService.get_events(user_id, db, days_ahead=30)
        if needs_memory_update:
            memory_task = MemoryService.get_memory_context(user_id, db, min_importance=0.3)

    # Wait for tasks
    if email_task:
        try:
            emails = await email_task
            if emails:
                email_context = "RECENT EMAILS:\n" + "\n".join([
                    f"- {e['subject']} from {e['from']}\n  {e['preview']}" for e in emails[:5]
                ])
            else:
                email_context = "No recent emails found."
        except Exception as e:
            email_context = f"Could not fetch emails: {str(e)}"

    if calendar_task:
        try:
            events = await calendar_task
            if events:
                calendar_context = "CALENDAR EVENTS:\n" + "\n".join([
                    f"- {e.get('summary', 'Event')}: {e.get('start', 'TBD')}" for e in events[:10]
                ])
            else:
                calendar_context = "No upcoming events."
        except Exception as e:
            calendar_context = f"Could not fetch calendar: {str(e)}"

    if memory_task:
        try:
            memory_context = await memory_task
        except:
            memory_context = ""

    # Build comprehensive system prompt
    system_prompt = f"""You are Cortex, a personal AI Chief of Staff assistant with access to user's email, calendar, and long-term memory.

Your capabilities:
1. Answer questions about emails, calendar, and preferences
2. Remember user preferences, constraints, and important context
3. Help manage the user's day and projects

USER CONTEXT:
Memory (your long-term memory about this user):
{memory_context if memory_context else "No prior memory stored."}

Email context:
{email_context if email_context else "Not asked about email."}

Calendar context:
{calendar_context if calendar_context else "Not asked about calendar."}

CRITICAL INSTRUCTIONS:
- If asked about calendar/meetings, USE the calendar context provided above
- If asked about emails, USE the email context provided above  
- If user mentions preferences (like "I prefer afternoon meetings"), acknowledge and remember them
- If user says things like "I'm on vacation until Jan 20th", extract this as a PREFERENCE with high importance
- Be helpful, concise, and proactive
- If you don't have information, clearly say so rather than making things up"""

    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain_core.messages import HumanMessage, SystemMessage

    try:
        llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=api_key)
        response = await llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=message)
        ])

        # Extract and store new memories AFTER responding (for next time)
        if needs_memory_update:
            try:
                await MemoryService.extract_facts(user_id, message, db, source="chat")
            except:
                pass

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
