from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import List, Optional
from langchain_core.messages import HumanMessage, AIMessage
from slowapi import Limiter
from slowapi.util import get_remote_address
from ..db.database import get_db
from ..db.models import User, ChatMessage
from ..services.memory_service import MemoryService
import uuid
from collections import deque
import os

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

MAX_CONVERSATION_LENGTH = 100

conversation_histories = {}

class MessageHistory(BaseModel):
    role: str
    content: str

class ConversationResponse(BaseModel):
    id: str
    title: str
    created_at: str

class ChatRequest(BaseModel):
    message: str
    user_id: str
    conversation_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    user_id: str
    conversation_id: str
    title: Optional[str] = None

async def get_or_create_user(user_id: str, db: AsyncSession) -> User:
    """Get or create user"""
    from sqlalchemy import select

    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        user_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, user_id)

    stmt = select(User).where(User.id == user_uuid)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        user = User(id=user_uuid, email=f"user-{user_id}@cortex.ai")
        db.add(user)
        await db.commit()

    return user

@router.post("/chat", response_model=ChatResponse)
async def chat(request: Request, chat_request: ChatRequest, db: AsyncSession = Depends(get_db)):
    """Chat endpoint using the intelligent LangGraph agent with multi-conversation support"""
    from ..agent.graph import run_agent
    from ..db.models import ChatMessage, Conversation
    from sqlalchemy import select, update
    import uuid

    user_id = chat_request.user_id
    message = chat_request.message
    conv_id = chat_request.conversation_id

    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        user_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, user_id)

    # 1. Handle Conversation
    new_conversation = False
    conv_uuid = None
    
    if conv_id:
        try:
            conv_uuid = uuid.UUID(conv_id)
        except (ValueError, TypeError):
            conv_uuid = None
            
    if not conv_uuid:
        conversation = Conversation(user_id=user_uuid, title="New Chat")
        db.add(conversation)
        await db.flush() # Get ID
        conv_uuid = conversation.id
        conv_id = str(conv_uuid)
        new_conversation = True

    # 2. Get history for this specific conversation
    stmt = select(ChatMessage).where(ChatMessage.conversation_id == conv_uuid).order_by(ChatMessage.created_at.asc())
    result = await db.execute(stmt)
    db_messages = result.scalars().all()
    
    history = []
    for msg in db_messages:
        history.append({"role": msg.role, "content": msg.content})
    
    # 3. Add current message to history for agent
    history.append({"role": "user", "content": message})

    try:
        # 4. Run Agent
        response_text = await run_agent(user_id, message, db, history)

        # 5. Save Messages to DB
        user_msg = ChatMessage(user_id=user_uuid, conversation_id=conv_uuid, role="user", content=message)
        ai_msg = ChatMessage(user_id=user_uuid, conversation_id=conv_uuid, role="assistant", content=response_text)
        
        db.add(user_msg)
        db.add(ai_msg)

        # 6. Auto-generate title if it's a new conversation
        generated_title = None
        if new_conversation:
            try:
                from langchain_google_genai import ChatGoogleGenerativeAI
                llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=os.getenv("GOOGLE_API_KEY"))
                title_prompt = f"Based on this first message: '{message}', generate a short 3-4 word title for the conversation. Return ONLY the title text, no quotes or prefix."
                title_res = await llm.ainvoke(title_prompt)
                generated_title = title_res.content.strip()
                if generated_title:
                    stmt = update(Conversation).where(Conversation.id == conv_uuid).values(title=generated_title)
                    await db.execute(stmt)
            except Exception as e:
                print(f"Title generation error: {e}")

        await db.commit()

        return ChatResponse(
            response=response_text, 
            user_id=user_id, 
            conversation_id=conv_id,
            title=generated_title
        )
        
    except Exception as e:
        import traceback
        import google.generativeai as genai
        
        print(f"Agent Error: {str(e)}")
        print(traceback.format_exc())
        
        if "404" in str(e) or "not found" in str(e).lower():
            try:
                print("--- DEBUG: CHECKING AVAILABLE MODELS ---")
                api_key = os.getenv("GOOGLE_API_KEY")
                if api_key:
                    genai.configure(api_key=api_key)
                    models = genai.list_models()
                    available_models = []
                    for m in models:
                        model_info = f"{m.name} (Methods: {m.supported_generation_methods})"
                        print(f"Found model: {model_info}")
                        if "generateContent" in m.supported_generation_methods:
                            available_models.append(m.name)
                    print(f"Models supporting generateContent: {available_models}")
                else:
                    print("GOOGLE_API_KEY not found in env")
                print("--- END DEBUG ---")
            except Exception as model_err:
                print(f"Failed to list models: {model_err}")
                
        raise HTTPException(status_code=500, detail=f"Agent Error: {str(e)}")

@router.get("/conversations/{user_id}", response_model=List[ConversationResponse])
async def get_conversations(user_id: str, db: AsyncSession = Depends(get_db)):
    """Get all conversations for a user"""
    from sqlalchemy import select
    from ..db.models import Conversation

    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        user_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, user_id)

    stmt = select(Conversation).where(Conversation.user_id == user_uuid).order_by(Conversation.updated_at.desc())
    result = await db.execute(stmt)
    conversations = result.scalars().all()

    return [
        ConversationResponse(
            id=str(c.id),
            title=c.title,
            created_at=c.created_at.isoformat()
        )
        for c in conversations
    ]

@router.get("/chat/history/{conversation_id}", response_model=List[MessageHistory])
async def get_conversation_history(conversation_id: str, db: AsyncSession = Depends(get_db)):
    """Get message history for a specific conversation"""
    from sqlalchemy import select
    
    try:
        conv_uuid = uuid.UUID(conversation_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid conversation ID")

    stmt = select(ChatMessage).where(ChatMessage.conversation_id == conv_uuid).order_by(ChatMessage.created_at)
    result = await db.execute(stmt)
    messages = result.scalars().all()

    return [
        MessageHistory(role=msg.role, content=msg.content)
        for msg in messages
    ]

@router.delete("/chat/history/{user_id}")
async def clear_chat_history(user_id: str, db: AsyncSession = Depends(get_db)):
    """Clear all chat history for user (all conversations and messages)"""
    from sqlalchemy import delete
    from ..db.models import Conversation, ChatMessage
    
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        user_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, user_id)

    # 1. Delete all chat messages for this user
    stmt1 = delete(ChatMessage).where(ChatMessage.user_id == user_uuid)
    await db.execute(stmt1)

    # 2. Delete all conversations for this user
    stmt2 = delete(Conversation).where(Conversation.user_id == user_uuid)
    await db.execute(stmt2)

    await db.commit()

    return {"status": "success", "message": "All chat history cleared"}

@router.delete("/user/data/{user_id}")
async def delete_all_user_data(user_id: str, db: AsyncSession = Depends(get_db)):
    """Delete all data for user (Chat + Memory + Conversations)"""
    from sqlalchemy import delete
    from ..db.models import MemoryFact, MemoryEmbedding, Conversation, ChatMessage
    
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        user_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, user_id)

    # 1. Delete Chat Messages
    stmt1 = delete(ChatMessage).where(ChatMessage.user_id == user_uuid)
    await db.execute(stmt1)

    # 2. Delete Conversations
    stmt_conv = delete(Conversation).where(Conversation.user_id == user_uuid)
    await db.execute(stmt_conv)

    # 3. Delete Memory Embeddings (linked to facts being deleted)
    # We exclude personal profile and preference facts from deletion
    from sqlalchemy import select, and_, not_
    fact_ids_stmt = select(MemoryFact.id).where(
        and_(
            MemoryFact.user_id == user_uuid,
            not_(MemoryFact.category.in_(["personal", "preference"]))
        )
    )
    fact_ids_result = await db.execute(fact_ids_stmt)
    fact_ids = fact_ids_result.scalars().all()

    if fact_ids:
        stmt2 = delete(MemoryEmbedding).where(MemoryEmbedding.memory_fact_id.in_(fact_ids))
        await db.execute(stmt2)

    # 4. Delete Memory Facts (excluding profile facts)
    stmt3 = delete(MemoryFact).where(
        and_(
            MemoryFact.user_id == user_uuid,
            not_(MemoryFact.category.in_(["personal", "preference"]))
        )
    )
    await db.execute(stmt3)

    await db.commit()

    return {"status": "success", "message": "All user data deleted"}
