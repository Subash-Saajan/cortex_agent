import os
from typing import List
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from sqlalchemy.ext.asyncio import AsyncSession
from ..db.models import User
from sqlalchemy import select

class CalendarService:
    """Service for Google Calendar API interactions"""

    @staticmethod
    async def get_service(user_id: str, db: AsyncSession):
        """Get Calendar service with user's credentials"""
        # Get user with refresh token
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user or not user.refresh_token:
            raise ValueError("User not authenticated with Google")

        # Create credentials from refresh token
        credentials = Credentials(
            token=None,
            refresh_token=user.refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=os.getenv("GOOGLE_CLIENT_ID"),
            client_secret=os.getenv("GOOGLE_CLIENT_SECRET")
        )

        # Refresh token if needed
        request = Request()
        credentials.refresh(request)

        return build("calendar", "v3", credentials=credentials)

    @staticmethod
    async def get_events(user_id: str, db: AsyncSession, days_ahead: int = 7) -> List[dict]:
        """Get upcoming events"""
        try:
            service = await CalendarService.get_service(user_id, db)

            now = datetime.utcnow().isoformat() + "Z"
            end = (datetime.utcnow() + timedelta(days=days_ahead)).isoformat() + "Z"

            # Get events
            events_result = service.events().list(
                calendarId="primary",
                timeMin=now,
                timeMax=end,
                maxResults=10,
                singleEvents=True,
                orderBy="startTime"
            ).execute()

            events = events_result.get("items", [])
            event_list = []

            for event in events:
                start = event["start"].get("dateTime", event["start"].get("date"))
                end = event["end"].get("dateTime", event["end"].get("date"))

                event_list.append({
                    "id": event["id"],
                    "title": event.get("summary", "No Title"),
                    "start": start,
                    "end": end,
                    "description": event.get("description", ""),
                    "location": event.get("location", "")
                })

            return event_list

        except Exception as e:
            raise ValueError(f"Error fetching events: {str(e)}")

    @staticmethod
    async def create_event(
        user_id: str,
        title: str,
        start_time: str,
        end_time: str,
        description: str = "",
        location: str = "",
        db: AsyncSession = None
    ) -> str:
        """Create a calendar event"""
        try:
            service = await CalendarService.get_service(user_id, db)

            event = {
                "summary": title,
                "description": description,
                "location": location,
                "start": {"dateTime": start_time},
                "end": {"dateTime": end_time}
            }

            created_event = service.events().insert(
                calendarId="primary",
                body=event
            ).execute()

            return created_event["id"]

        except Exception as e:
            raise ValueError(f"Error creating event: {str(e)}")
