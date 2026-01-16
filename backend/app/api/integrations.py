from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from ..db.database import get_db
from ..services.gmail_service import GmailService
from ..services.calendar_service import CalendarService
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
import os

router = APIRouter()

class EmailSendRequest(BaseModel):
    user_id: str
    to: str
    subject: str
    body: str

class EventCreateRequest(BaseModel):
    user_id: str
    title: str
    start_time: str
    end_time: str
    description: str = ""
    location: str = ""

class AnalyzeEmailRequest(BaseModel):
    user_id: str
    message_id: str
    question: str = "Summarize this email and attachments"

# Gmail Endpoints
@router.get("/gmail/inbox/{user_id}")
async def get_inbox(user_id: str, db: AsyncSession = Depends(get_db)):
    """Get inbox emails"""
    try:
        emails = await GmailService.get_inbox(user_id, db)
        return {"emails": emails}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/gmail/send")
async def send_email(request: EmailSendRequest, db: AsyncSession = Depends(get_db)):
    """Send an email"""
    try:
        message_id = await GmailService.send_email(
            request.user_id,
            request.to,
            request.subject,
            request.body,
            db
        )
        return {"message_id": message_id, "status": "sent"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Calendar Endpoints
@router.get("/calendar/events/{user_id}")
async def get_events(user_id: str, days_ahead: int = 7, db: AsyncSession = Depends(get_db)):
    """Get upcoming calendar events"""
    try:
        events = await CalendarService.get_events(user_id, db, days_ahead)
        return {"events": events}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/calendar/create")
async def create_event(request: EventCreateRequest, db: AsyncSession = Depends(get_db)):
    """Create a calendar event"""
    try:
        event_id = await CalendarService.create_event(
            request.user_id,
            request.title,
            request.start_time,
            request.end_time,
            request.description,
            request.location,
            db
        )
        return {"event_id": event_id, "status": "created"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/gmail/analyze")
async def analyze_email(request: AnalyzeEmailRequest, db: AsyncSession = Depends(get_db)):
    """Analyze email and attachments with Gemini"""
    try:
        # Get message with attachments
        message = await GmailService.get_message_with_attachments(
            request.user_id,
            request.message_id,
            db
        )

        # Build content for analysis
        content = f"Subject: {message['subject']}\n"
        content += f"From: {message['from']}\n"
        content += f"Date: {message['date']}\n\n"
        content += f"Body:\n{message['body']}\n\n"

        if message['attachments']:
            for att in message['attachments']:
                content += f"\n--- Attachment: {att['filename']} ---\n"
                content += f"{att['text']}\n"

        content += f"\n\nQuestion: {request.question}"

        # Analyze with Gemini
        llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash-001", google_api_key=os.getenv("GOOGLE_API_KEY"))
        response = await llm.ainvoke([HumanMessage(content=content)])

        return {
            "message": {
                "subject": message["subject"],
                "from": message["from"],
                "date": message["date"]
            },
            "analysis": response.content
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
