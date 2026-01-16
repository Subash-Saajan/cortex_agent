import os
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from ..db.models import MemoryFact, MemoryEmbedding
import json
import uuid

from langchain_google_genai import GoogleGenerativeAIEmbeddings

llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=os.getenv("GOOGLE_API_KEY"))
embeddings_model = GoogleGenerativeAIEmbeddings(model="models/embedding-001")

class MemoryNode:
    """A node in the memory graph"""
    def __init__(self, fact: str, category: str, importance: float, source: str, metadata: Dict[str, Any] = None):
        self.id = str(uuid.uuid4())
        self.fact = fact
        self.category = category  # preference, habit, project, relationship, constraint, event
        self.importance = importance  # 0.0 to 1.0
        self.source = source  # chat, email, calendar
        self.metadata = metadata or {}
        self.created_at = None
        self.updated_at = None
        self.connections = []  # connected memory node IDs

class MemoryGraph:
    """Graph-based memory system for the agent"""
    
    def __init__(self):
        self.nodes: Dict[str, MemoryNode] = {}
    
    def add_node(self, node: MemoryNode):
        """Add a memory node"""
        self.nodes[node.id] = node
        return node
    
    def connect_nodes(self, node_id1: str, node_id2: str):
        """Connect two memory nodes"""
        if node_id1 in self.nodes and node_id2 in self.nodes:
            self.nodes[node_id1].connections.append(node_id2)
            self.nodes[node_id2].connections.append(node_id1)
    
    def get_related_memories(self, category: str = None, min_importance: float = 0.0) -> List[MemoryNode]:
        """Get memories filtered by category and importance"""
        results = []
        for node in self.nodes.values():
            if node.importance >= min_importance:
                if category is None or node.category == category:
                    results.append(node)
        return sorted(results, key=lambda x: x.importance, reverse=True)
    
    def search_memories(self, query: str) -> List[MemoryNode]:
        """Search memories by keyword"""
        query_lower = query.lower()
        results = []
        for node in self.nodes.values():
            if query_lower in node.fact.lower() or query_lower in node.category:
                results.append(node)
        return sorted(results, key=lambda x: x.importance, reverse=True)

class MemoryService:
    """Service for managing user memory with embeddings"""

    @staticmethod
    async def extract_facts(user_id: str, message: str, db: AsyncSession, source: str = "chat") -> List[MemoryNode]:
        """Extract facts from message using Gemini and store in memory graph"""

        prompt = f"""You are analyzing a message to extract important facts about the user.
Extract facts that would be useful for a personal assistant.

Message: {message}

Return as JSON array with objects containing:
- fact: the extracted information (concise, specific)
- category: one of ["preference", "habit", "project", "relationship", "constraint", "event", "personal"]
- importance: 0.0 to 1.0 (how important is this fact)
- metadata: any additional context

Examples:
- "I hate 9 AM meetings" → {{"fact": "User dislikes morning meetings before 10 AM", "category": "preference", "importance": 0.9, "metadata": {{"time": "9 AM"}}}}
- "Project X is delayed" → {{"fact": "Project X has delays", "category": "project", "importance": 0.8, "metadata": {{"project": "Project X"}}}}
- "John is the PM" → {{"fact": "John is the project manager", "category": "relationship", "importance": 0.7, "metadata": {{"person": "John", "role": "PM"}}}}

Only return JSON, no other text. If no important facts, return []."""

        response = await llm.ainvoke([HumanMessage(content=prompt)])

        try:
            content = getattr(response, 'content', str(response))
            # Clean JSON if wrapped in code blocks
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
                
            facts_data = json.loads(content)
            if not isinstance(facts_data, list):
                return []
            
            memory_nodes = []
            for fact_data in facts_data:
                node = MemoryNode(
                    fact=fact_data.get("fact", ""),
                    category=fact_data.get("category", "personal"),
                    importance=fact_data.get("importance", 0.5),
                    source=source,
                    metadata=fact_data.get("metadata", {})
                )
                memory_nodes.append(node)
                
                # Store in database
                await MemoryService.store_fact(user_id, node.fact, node.category, node.importance, node.metadata, db)
            
            return memory_nodes
        except (json.JSONDecodeError, AttributeError) as e:
            print(f"Error parsing facts: {e}")
            return []

    @staticmethod
    async def store_fact(user_id: str, fact: str, category: str, importance: float = 0.5, metadata: Dict = None, db: AsyncSession = None) -> MemoryFact:
        """Store a fact in the database with its embedding"""
        try:
            user_uuid = uuid.UUID(user_id)
        except ValueError:
            user_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, user_id)

        # Generate embedding
        embedding = await embeddings_model.aembed_query(fact)

        memory_fact = MemoryFact(
            user_id=user_uuid,
            fact=fact,
            category=category,
            importance=importance,
            metadata_json=json.dumps(metadata or {})
        )

        if db:
            db.add(memory_fact)
            await db.flush() # Get the ID
            
            # Store embedding
            memory_embedding = MemoryEmbedding(
                memory_fact_id=memory_fact.id,
                embedding=embedding
            )
            db.add(memory_embedding)
            
            await db.commit()
            await db.refresh(memory_fact)

        return memory_fact

    @staticmethod
    async def search_semantic_memories(user_id: str, query: str, db: AsyncSession, limit: int = 5) -> List[str]:
        """Search memories using semantic similarity (pgvector)"""
        try:
            user_uuid = uuid.UUID(user_id)
        except ValueError:
            user_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, user_id)

        # Generate query embedding
        query_embedding = await embeddings_model.aembed_query(query)

        # Using pgvector's <-> operator for L2 distance (or <=> for cosine similarity if preferred)
        # We need to join MemoryFact and MemoryEmbedding
        stmt = select(MemoryFact).join(
            MemoryEmbedding, MemoryFact.id == MemoryEmbedding.memory_fact_id
        ).where(
            MemoryFact.user_id == user_uuid
        ).order_by(
            MemoryEmbedding.embedding.l2_distance(query_embedding)
        ).limit(limit)
        
        result = await db.execute(stmt)
        facts = result.scalars().all()

        return [f.fact for f in facts] if facts else []

    @staticmethod
    async def retrieve_relevant_facts(user_id: str, query: str, db: AsyncSession, limit: int = 10) -> List[str]:
        """Retrieve relevant facts for a query (hybrid of semantic and importance)"""
        semantic_facts = await MemoryService.search_semantic_memories(user_id, query, db, limit=limit//2)
        
        # Also get high importance facts
        try:
            user_uuid = uuid.UUID(user_id)
        except ValueError:
            user_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, user_id)

        stmt = select(MemoryFact).where(
            MemoryFact.user_id == user_uuid
        ).order_by(MemoryFact.importance.desc()).limit(limit//2)
        
        result = await db.execute(stmt)
        importance_facts = [f.fact for f in result.scalars().all()]
        
        # Combine and deduplicate
        combined = list(set(semantic_facts + importance_facts))
        return combined

    @staticmethod
    async def get_memory_context(user_id: str, db: AsyncSession, min_importance: float = 0.5) -> str:
        """Get formatted memory context for agent"""
        try:
            user_uuid = uuid.UUID(user_id)
        except ValueError:
            user_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, user_id)

        stmt = select(MemoryFact).where(
            MemoryFact.user_id == user_uuid,
            MemoryFact.importance >= min_importance
        ).order_by(MemoryFact.importance.desc()).limit(20)
        
        result = await db.execute(stmt)
        facts = result.scalars().all()

        if not facts:
            return "No prior context available."

        # Group by category
        by_category = {}
        for f in facts:
            if f.category not in by_category:
                by_category[f.category] = []
            by_category[f.category].append(f.fact)

        context_lines = ["User Profile & Context:"]
        for category, fact_list in by_category.items():
            context_lines.append(f"\n[{category.upper()}]:")
            for fact in fact_list:
                context_lines.append(f"  • {fact}")

        return "\n".join(context_lines)

    @staticmethod
    async def get_constraint_context(user_id: str, db: AsyncSession) -> str:
        """Get only constraints and preferences for email drafting"""
        try:
            user_uuid = uuid.UUID(user_id)
        except ValueError:
            user_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, user_id)

        stmt = select(MemoryFact).where(
            MemoryFact.user_id == user_uuid,
            MemoryFact.category.in_(["preference", "constraint", "habit"]),
            MemoryFact.importance >= 0.7
        ).order_by(MemoryFact.importance.desc())
        
        result = await db.execute(stmt)
        facts = result.scalars().all()

        if not facts:
            return ""

        constraints = ["User constraints and preferences:"]
        for f in facts:
            constraints.append(f"  • {f.fact}")
        
        return "\n".join(constraints)

