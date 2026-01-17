from fastapi import APIRouter, HTTPException, Depends, Query, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
import os
import jwt
from datetime import datetime, timedelta
from google.auth.transport import requests as google_requests
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
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://cortex.subashsaajan.site")
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
    is_setup_complete: bool = False

class SetupRequest(BaseModel):
    user_id: str
    job_title: str
    main_goal: str
    work_hours: str

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
    import logging
    import traceback
    logger = logging.getLogger("cortex-api")
    
    logger.info(f"Login attempt - CLIENT_ID set: {bool(GOOGLE_CLIENT_ID)}, SECRET set: {bool(GOOGLE_CLIENT_SECRET)}")
    
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        logger.error(f"OAuth not configured - CLIENT_ID: {bool(GOOGLE_CLIENT_ID)}, SECRET: {bool(GOOGLE_CLIENT_SECRET)}")
        raise HTTPException(status_code=500, detail="Google OAuth not configured")

    # Create OAuth 2.0 flow
    scopes = [
        "openid",
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

@router.get("/callback")
async def callback(code: str = Query(...), db: AsyncSession = Depends(get_db)):
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
            "openid",
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/userinfo.profile",
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/gmail.send",
            "https://www.googleapis.com/auth/calendar"
        ])
        flow.redirect_uri = GOOGLE_REDIRECT_URI

        # Get token from authorization code
        try:
            flow.fetch_token(code=code)
            credentials = flow.credentials
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"OAuth token exchange failed: {str(e)}")

        # Get user info from id_token
        try:
            user_info = verify_oauth2_token(credentials.id_token, google_requests.Request(), GOOGLE_CLIENT_ID)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Token verification failed: {str(e)}")

        if not user_info:
            raise HTTPException(status_code=400, detail="Invalid token information")

        email = user_info.get("email")
        google_id = user_info.get("sub")
        name = user_info.get("name")

        if not email or not google_id:
            raise HTTPException(status_code=400, detail="Missing required user information")

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
            # Update existing user's refresh token if provided
            if credentials.refresh_token:
                user.refresh_token = credentials.refresh_token
            user.updated_at = datetime.utcnow()

        await db.commit()

        # Create JWT token
        access_token = create_access_token(str(user.id), user.email)

        # Build redirect URL with query parameters
        redirect_url = f"{FRONTEND_URL}?token={access_token}&user_id={str(user.id)}&is_setup_complete={1 if user.is_setup_complete else 0}"
        
        # Check if user has valid refresh token for API access
        if not user.refresh_token:
            # User authenticated but no refresh token - warn them
            redirect_url += "&warning=Please+sign+in+again+to+enable+Gmail+and+Calendar+features"
        
        return RedirectResponse(url=redirect_url)

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = str(e)
        # If it's the "'str' object is not callable" error, provide more context
        if "'str' object is not callable" in str(e):
            error_detail = "OAuth configuration error. Please check your Google OAuth credentials and configuration."
        
        error_url = f"{FRONTEND_URL}?error={error_detail}"
        return RedirectResponse(url=error_url)

@router.get("/verify")
async def verify_token_endpoint(token: str = Query(...)):
    """Verify JWT token"""
    payload = verify_token(token)
    return {"user_id": payload["user_id"], "email": payload["email"]}

@router.get("/user/{user_id}")
async def get_user(user_id: str, db: AsyncSession = Depends(get_db)):
    """Get user info by user_id"""
    try:
        stmt = select(User).where(User.id == uuid.UUID(user_id))
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {
            "id": str(user.id),
            "email": user.email,
            "name": user.name,
            "is_setup_complete": bool(user.is_setup_complete)
        }
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user_id format")

@router.post("/setup")
async def setup_user(req: SetupRequest, db: AsyncSession = Depends(get_db)):
    """Complete user account setup"""
    try:
        stmt = select(User).where(User.id == uuid.UUID(req.user_id))
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
            
        user.job_title = req.job_title
        user.main_goal = req.main_goal
        user.work_hours = req.work_hours
        user.is_setup_complete = 1
        
        # Also save this to memory for the AI
        from ..services.memory_service import MemoryService
        await MemoryService.store_fact(
            str(user.id), 
            f"User Profile: I am a {req.job_title}. My main goal is {req.main_goal}. I typically work {req.work_hours}.", 
            category="personal",
            db=db
        )
        
        await db.commit()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
