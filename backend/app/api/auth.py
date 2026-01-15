from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
import os
import jwt
from datetime import datetime, timedelta
from google.auth.transport.requests import Request
from google.oauth2.id_token import verify_oauth2_token
from google_auth_oauthlib.flow import Flow
import json
from ..db.database import get_db
from ..db.models import User
import uuid

router = APIRouter()

# Google OAuth configuration
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "https://d3ouv9vt88djdf.cloudfront.net/api/auth/callback")
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key")
JWT_ALGORITHM = "HS256"

class LoginResponse(BaseModel):
    auth_url: str

class CallbackRequest(BaseModel):
    code: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str

def create_access_token(user_id: str, email: str, expires_delta: timedelta = None):
    """Create JWT access token"""
    if expires_delta is None:
        expires_delta = timedelta(days=7)

    expire = datetime.utcnow() + expires_delta
    payload = {
        "user_id": user_id,
        "email": email,
        "exp": expire,
        "iat": datetime.utcnow()
    }
    encoded_jwt = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> dict:
    """Verify JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

@router.get("/login")
async def login():
    """Generate Google OAuth URL"""
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise HTTPException(status_code=500, detail="Google OAuth not configured")

    # Create OAuth 2.0 flow
    scopes = [
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile",
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.send",
        "https://www.googleapis.com/auth/calendar"
    ]

    client_config = {
        "installed": {
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "redirect_uris": [GOOGLE_REDIRECT_URI],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token"
        }
    }
    flow = Flow.from_client_config(client_config, scopes=scopes)
    flow.redirect_uri = GOOGLE_REDIRECT_URI

    auth_url, state = flow.authorization_url(prompt="consent")

    return LoginResponse(auth_url=auth_url)

@router.post("/callback")
async def callback(request: CallbackRequest, db: AsyncSession = Depends(get_db)):
    """Handle Google OAuth callback"""
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise HTTPException(status_code=500, detail="Google OAuth not configured")

    try:
        # Create OAuth 2.0 flow
        client_config = {
            "installed": {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uris": [GOOGLE_REDIRECT_URI],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token"
            }
        }
        flow = Flow.from_client_config(client_config, scopes=[
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/userinfo.profile",
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/gmail.send",
            "https://www.googleapis.com/auth/calendar"
        ])
        flow.redirect_uri = GOOGLE_REDIRECT_URI

        # Get token from authorization code
        flow.fetch_token(code=request.code)
        credentials = flow.credentials

        # Get user info
        from google.oauth2.service_account import Credentials as ServiceAccountCredentials
        from googleapiclient.discovery import build

        service = build("oauth2", "v1", credentials=credentials)
        user_info = service.userinfo().get().execute()

        email = user_info.get("email")
        google_id = user_info.get("id")
        name = user_info.get("name")

        # Get or create user
        stmt = select(User).where(User.google_id == google_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            user = User(
                id=uuid.uuid4(),
                email=email,
                name=name,
                google_id=google_id,
                refresh_token=credentials.refresh_token
            )
            db.add(user)
        else:
            user.refresh_token = credentials.refresh_token
            user.updated_at = datetime.utcnow()

        await db.commit()

        # Create JWT token
        access_token = create_access_token(str(user.id), user.email)

        return TokenResponse(
            access_token=access_token,
            user_id=str(user.id),
            email=user.email
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"OAuth error: {str(e)}")

@router.get("/verify")
async def verify_token_endpoint(token: str = Query(...)):
    """Verify JWT token"""
    payload = verify_token(token)
    return {"user_id": payload["user_id"], "email": payload["email"]}
