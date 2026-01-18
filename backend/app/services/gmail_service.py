import base64
import os
from typing import List, Optional
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from sqlalchemy.ext.asyncio import AsyncSession
from ..db.models import User
from sqlalchemy import select
import io
from pypdf import PdfReader

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
    async def search_messages(user_id: str, db: AsyncSession, query: str = "in:inbox", max_results: int = 10) -> List[dict]:
        """Search for messages using Gmail query syntax (e.g., 'in:inbox', 'from:someone', 'subject:something')"""
        try:
            service = await GmailService.get_service(user_id, db)

            # Get message list
            results = service.users().messages().list(
                userId="me",
                maxResults=max_results,
                q=query
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
                receiver = next((h["value"] for h in headers if h["name"] == "To"), "Unknown")
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
                    "thread_id": msg["threadId"],
                    "subject": subject,
                    "from": sender,
                    "to": receiver,
                    "date": date,
                    "preview": body[:300] + "..." if len(body) > 300 else body
                })

            return email_list

        except Exception as e:
            raise ValueError(f"Error searching messages: {str(e)}")

    async def send_email(user_id: str, to: str, subject: str, body: str, db: AsyncSession, thread_id: str = None) -> str:
        """Send an email, supporting threading"""
        try:
            import re
            from email.mime.text import MIMEText
            service = await GmailService.get_service(user_id, db)

            # Robust email extraction: extract subash@example.com from "Subash <subash@example.com>"
            email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', to)
            clean_to = email_match.group(0) if email_match else to.strip()

            message = MIMEText(body)
            message["to"] = clean_to
            message["subject"] = subject

            # If replying, set proper headers
            if thread_id:
                try:
                    orig_msg = service.users().messages().get(userId="me", id=thread_id).execute()
                    orig_headers = orig_msg["payload"]["headers"]
                    msg_id_val = next((h["value"] for h in orig_headers if h["name"].lower() == "message-id"), None)
                    
                    if msg_id_val:
                        message["In-Reply-To"] = msg_id_val
                        message["References"] = msg_id_val
                    
                    if not subject.lower().startswith("re:"):
                        message["subject"] = "Re: " + subject
                except Exception as e:
                    print(f"Threading error (proceeding as new mail): {e}")

            raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
            send_message = {"raw": raw}
            if thread_id:
                send_message["threadId"] = thread_id

            result = service.users().messages().send(
                userId="me",
                body=send_message
            ).execute()

            return result["id"]

        except Exception as e:
            raise ValueError(f"Error sending email: {str(e)}")

    @staticmethod
    async def get_attachment(user_id: str, message_id: str, attachment_id: str, db: AsyncSession) -> str:
        """Get PDF attachment and extract text"""
        try:
            service = await GmailService.get_service(user_id, db)

            # Download attachment
            attachment = service.users().messages().attachments().get(
                userId="me",
                messageId=message_id,
                id=attachment_id
            ).execute()

            # Decode base64
            data = base64.urlsafe_b64decode(attachment["data"])

            # Extract text from PDF
            pdf_file = io.BytesIO(data)
            reader = PdfReader(pdf_file)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"

            return text

        except Exception as e:
            raise ValueError(f"Error extracting PDF: {str(e)}")

    @staticmethod
    async def get_message_with_attachments(user_id: str, message_id: str, db: AsyncSession) -> dict:
        """Get full message with attachment text extracted"""
        try:
            service = await GmailService.get_service(user_id, db)

            msg_data = service.users().messages().get(
                userId="me",
                id=message_id,
                format="full"
            ).execute()

            headers = msg_data["payload"]["headers"]
            subject = next((h["value"] for h in headers if h["name"] == "Subject"), "No Subject")
            sender = next((h["value"] for h in headers if h["name"] == "From"), "Unknown")
            date = next((h["value"] for h in headers if h["name"] == "Date"), "")

            attachments = []
            if "parts" in msg_data["payload"]:
                for part in msg_data["payload"]["parts"]:
                    if part["mimeType"] == "application/pdf":
                        attachment_id = part["body"]["attachmentId"]
                        filename = part.get("filename", "attachment.pdf")
                        text = await GmailService.get_attachment(user_id, message_id, attachment_id, db)
                        attachments.append({
                            "filename": filename,
                            "text": text
                        })

            # Get body
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

            return {
                "id": message_id,
                "subject": subject,
                "from": sender,
                "date": date,
                "body": body,
                "attachments": attachments
            }

        except Exception as e:
            raise ValueError(f"Error getting message: {str(e)}")
