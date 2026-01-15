import base64
import os
from typing import List, Optional
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from sqlalchemy.ext.asyncio import AsyncSession
from ..db.models import User
from sqlalchemy import select

class GmailService:
    """Service for Gmail API interactions"""

    @staticmethod
    async def get_service(user_id: str, db: AsyncSession):
        """Get Gmail service with user's credentials"""
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

        return build("gmail", "v1", credentials=credentials)

    @staticmethod
    async def get_inbox(user_id: str, db: AsyncSession, max_results: int = 10) -> List[dict]:
        """Get recent emails from inbox"""
        try:
            service = await GmailService.get_service(user_id, db)

            # Get message list
            results = service.users().messages().list(
                userId="me",
                maxResults=max_results,
                q="in:inbox"
            ).execute()

            messages = results.get("messages", [])
            email_list = []

            for msg in messages:
                msg_data = service.users().messages().get(
                    userId="me",
                    id=msg["id"],
                    format="full"
                ).execute()

                headers = msg_data["payload"]["headers"]
                subject = next((h["value"] for h in headers if h["name"] == "Subject"), "No Subject")
                sender = next((h["value"] for h in headers if h["name"] == "From"), "Unknown")
                date = next((h["value"] for h in headers if h["name"] == "Date"), "")

                # Get email body
                body = ""
                if "parts" in msg_data["payload"]:
                    for part in msg_data["payload"]["parts"]:
                        if part["mimeType"] == "text/plain":
                            if "data" in part["body"]:
                                body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")
                            break
                else:
                    if "body" in msg_data["payload"]:
                        body = base64.urlsafe_b64decode(msg_data["payload"]["body"]["data"]).decode("utf-8")

                email_list.append({
                    "id": msg["id"],
                    "subject": subject,
                    "from": sender,
                    "date": date,
                    "preview": body[:200] + "..." if len(body) > 200 else body
                })

            return email_list

        except Exception as e:
            raise ValueError(f"Error fetching inbox: {str(e)}")

    @staticmethod
    async def send_email(user_id: str, to: str, subject: str, body: str, db: AsyncSession) -> str:
        """Send an email"""
        try:
            from email.mime.text import MIMEText

            service = await GmailService.get_service(user_id, db)

            message = MIMEText(body)
            message["to"] = to
            message["subject"] = subject

            raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
            send_message = {"raw": raw}

            result = service.users().messages().send(
                userId="me",
                body=send_message
            ).execute()

            return result["id"]

        except Exception as e:
            raise ValueError(f"Error sending email: {str(e)}")
