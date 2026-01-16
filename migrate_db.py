import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("DATABASE_URL not found")
    exit(1)

# Ensure it uses asyncpg
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

async def migrate():
    engine = create_async_engine(DATABASE_URL)
    async with engine.begin() as conn:
        print("Checking for missing columns...")
        
        # Add metadata_json to memory_facts if it doesn't exist
        try:
            await conn.execute(text("ALTER TABLE memory_facts ADD COLUMN IF NOT EXISTS metadata_json TEXT"))
            print("Ensured metadata_json exists in memory_facts")
        except Exception as e:
            print(f"Error adding metadata_json: {e}")

        # Check for updated_at
        try:
            await conn.execute(text("ALTER TABLE memory_facts ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"))
            print("Ensured updated_at exists in memory_facts")
        except Exception as e:
            print(f"Error adding updated_at: {e}")

        # Ensure memory_embeddings table exists correctly
        # If the user changed from 1536 to 768, we might need to recreate the embedding column or table
        try:
            # Check current dimension
            result = await conn.execute(text("SELECT atttypmod FROM pg_attribute WHERE attrelid = 'memory_embeddings'::regclass AND attname = 'embedding'"))
            row = result.fetchone()
            if row:
                current_dim = row[0]
                print(f"Current embedding dimension: {current_dim}")
                if current_dim != 768:
                    print(f"Dimension mismatch! Expected 768, got {current_dim}. Recreating table...")
                    await conn.execute(text("DROP TABLE IF EXISTS memory_embeddings"))
                    print("Dropped memory_embeddings")
            else:
                print("embedding column not found in memory_embeddings")
        except Exception as e:
            print(f"Table check error: {e}")

        # Base.metadata.create_all will take care of creating the tables if they were dropped
        from backend.app.db.models import Base
        await conn.run_sync(Base.metadata.create_all)
        print("Schema creation/sync complete.")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(migrate())
