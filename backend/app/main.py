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
        # Enable pgvector extension
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        
        # --- MIGRATIONS ---
        # 1. Ensure metadata_json exists in memory_facts
        try:
            await conn.execute(text("ALTER TABLE memory_facts ADD COLUMN IF NOT EXISTS metadata_json TEXT"))
            logger.info("Checked memory_facts.metadata_json")
        except Exception as e:
            logger.error(f"Migration error (metadata_json): {e}")

        # 2. Add updated_at if missing
        try:
            await conn.execute(text("ALTER TABLE memory_facts ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"))
        except Exception as e:
            logger.error(f"Migration error (updated_at): {e}")

        # 3. Handle Vector dimension change (from 1536 to 768)
        try:
            # Drop and recreate embeddings table if dimension is wrong to avoid mismatches
            # In a real prod app we'd be more careful, but for this demo it's best to be clean.
            result = await conn.execute(text("SELECT atttypmod FROM pg_attribute WHERE attrelid = 'memory_embeddings'::regclass AND attname = 'embedding'"))
            row = result.fetchone()
            if row and row[0] != 768:
                logger.info(f"Vector dimension mismatch (found {row[0]}, expected 768). Recreating table...")
                await conn.execute(text("DROP TABLE IF EXISTS memory_embeddings CASCADE"))
        except Exception:
            # Table might not exist yet, create_all will handle it
            pass

        # Sync all models
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
    uvicorn.run(app, host="0.0.0.0", port=8000, proxy_headers=True, forwarded_allow_ips="*")
