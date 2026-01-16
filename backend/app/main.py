from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os
import logging
import traceback
from dotenv import load_dotenv
from sqlalchemy import text
from .db.database import engine, Base
from .api.chat import router as chat_router
from .api.auth import router as auth_router
from .api.integrations import router as integrations_router

load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("cortex-api")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Initializing database and pgvector...")
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database initialized.")
    yield
    # Shutdown
    await engine.dispose()

app = FastAPI(title="Cortex Agent API", lifespan=lifespan)

# CORS configuration
origins = [
    "https://cortex.subashsaajan.site",
    "https://api.cortex.subashsaajan.site",
    "https://d3ouv9vt88djdf.cloudfront.net",
    "http://localhost:3000",
    "http://localhost:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Global Error Handler to ensure CORS headers are present even on 500s
@app.middleware("http")
async def error_handling_middleware(request: Request, call_next):
    try:
        logger.info(f"Request: {request.method} {request.url.path}")
        response = await call_next(request)
        return response
    except Exception as e:
        logger.error(f"Unhandled exception: {str(e)}")
        logger.error(traceback.format_exc())
        
        # Manual CORS for error response
        origin = request.headers.get("origin")
        content = f'{{"detail": "Internal Server Error: {str(e)}"}}'
        headers = {
            "Content-Type": "application/json",
            "Access-Control-Allow-Credentials": "true",
        }
        if origin in origins:
            headers["Access-Control-Allow-Origin"] = origin
            
        return Response(
            content=content,
            status_code=500,
            headers=headers
        )

# Include routers
app.include_router(chat_router, prefix="/api", tags=["chat"])
app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(integrations_router, prefix="/api", tags=["integrations"])

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "cortex-agent-api"}

if __name__ == "__main__":
    import uvicorn
    # Use proxy_headers if behind ALB
    uvicorn.run(app, host="0.0.0.0", port=8000, proxy_headers=True, forwarded_allow_ips="*")
