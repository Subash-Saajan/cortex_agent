from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from ..db.database import get_db
from ..services.gmail_service import GmailService
from ..services.calendar_service import CalendarService

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
