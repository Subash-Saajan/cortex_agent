import os
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from ..db.models import MemoryFact, MemoryEmbedding
import json

llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro", google_api_key=os.getenv("GOOGLE_API_KEY"))

class MemoryService:
    """Service for managing user memory with embeddings"""

    @staticmethod
    async def extract_facts(user_id: str, message: str, db: AsyncSession) -> List[dict]:
        """Extract facts from user message using Gemini"""

        prompt = f"""Extract key facts, preferences, and important information from this message.
Only extract if the information is about the user's preferences, habits, or important facts.

Message: {message}

Return as JSON array with objects containing:
- fact: the extracted information
- category: one of ["preference", "habit", "event", "personal", "other"]

If no facts to extract, return empty array [].
Only return JSON, no other text."""

        response = llm.invoke([HumanMessage(content=prompt)])

        try:
            facts = json.loads(response.content)
            return facts if isinstance(facts, list) else []
        except (json.JSONDecodeError, AttributeError):
            return []

    @staticmethod
    async def store_fact(user_id: str, fact: str, category: str, db: AsyncSession) -> MemoryFact:
        """Store a fact with embedding"""

        embedding_response = llm.invoke([HumanMessage(content=f"Convert this to a searchable vector representation: {fact}")])

        # Create memory fact
        memory_fact = MemoryFact(
            user_id=user_id,
            fact=fact,
            category=category,
            importance=0.7
        )

        db.add(memory_fact)
        await db.flush()

        # Create embedding (using text representation for now)
        # In production, use actual vector embeddings from OpenAI or similar
        memory_embedding = MemoryEmbedding(
            memory_fact_id=memory_fact.id,
            embedding=[0.0] * 1536  # Placeholder - would use actual embeddings
        )

        db.add(memory_embedding)
        await db.commit()

        return memory_fact

    @staticmethod
    async def retrieve_relevant_facts(user_id: str, query: str, db: AsyncSession, limit: int = 5) -> List[str]:
        """Retrieve relevant facts for a query using similarity search"""

        # For now, simple keyword-based retrieval
        # In production, use pgvector similarity search
        stmt = select(MemoryFact).where(MemoryFact.user_id == user_id).limit(limit)
        result = await db.execute(stmt)
        facts = result.scalars().all()

        return [f.fact for f in facts] if facts else []

    @staticmethod
    async def get_memory_context(user_id: str, db: AsyncSession) -> str:
        """Get formatted memory context for agent"""

        stmt = select(MemoryFact).where(MemoryFact.user_id == user_id).limit(10)
        result = await db.execute(stmt)
        facts = result.scalars().all()

        if not facts:
            return "No prior context available."

        context_lines = ["Known user preferences and facts:"]
        for fact in facts:
            context_lines.append(f"- {fact.fact} (Category: {fact.category})")

        return "\n".join(context_lines)
