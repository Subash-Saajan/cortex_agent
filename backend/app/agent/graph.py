from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from typing import TypedDict, List, Any
import json
import os

class AgentState(TypedDict):
    """State for the agent"""
    user_id: str
    messages: List[Any]
    input: str
    memory_context: str
    email_context: str
    calendar_context: str
    response: str
    needs_memory_update: bool
    needs_email_read: bool
    needs_email_send: bool
    draft_email: str

def get_llm():
    """Get LLM instance - lazily initialized"""
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=os.getenv("GOOGLE_API_KEY")
    )

SYSTEM_PROMPT = """You are Cortex, a personal AI Chief of Staff assistant.

Your capabilities:
1. Answer questions about emails and calendar
2. Draft and send emails based on user requests
3. Remember user preferences, constraints, and important context
4. Help manage the user's day and projects

Available memory about the user:
{memory_context}

Email context (if any):
{email_context}

Calendar context (if any):
{calendar_context}

Guidelines:
- Be concise and helpful
- If asked about emails or calendar, use the provided context
- Remember important constraints and preferences the user mentions
- For email drafting, consider user's known preferences and constraints"""

def analyze_intent(state: AgentState) -> dict:
    """Analyze user intent to determine what actions are needed"""
    user_input = state["input"].lower()
    
    needs_email_read = any(word in user_input for word in [
        "latest email", "recent email", "unread email", "my email", 
        "inbox", "check email", "what's in my email", "any new email",
        "summarize email", "read email", "show me email"
    ])
    
    needs_email_send = any(phrase in user_input for phrase in [
        "send an email", "send email", "draft an email", "write an email",
        "compose email", "email to", "send mail", "reply to"
    ])
    
    needs_memory_update = any(word in user_input for word in [
        "i prefer", "i don't like", "i hate", "i like", "remember",
        "always", "never", "i want", "i need", "make sure",
        "important", "don't forget", "keep in mind"
    ])
    
    return {
        **state,
        "needs_email_read": needs_email_read,
        "needs_email_send": needs_email_send,
        "needs_memory_update": needs_memory_update
    }

async def fetch_email_context(state: AgentState, db) -> AgentState:
    """Fetch relevant emails for the query"""
    from ..services.gmail_service import GmailService
    
    try:
        emails = await GmailService.get_inbox(state["user_id"], db, max_results=5)
        
        if emails:
            email_text = "RECENT EMAILS:\n" + "\n".join([
                f"- {e['subject']} from {e['from']}\n  {e['preview']}" for e in emails[:5]
            ])
            state["email_context"] = email_text
        else:
            state["email_context"] = "No recent emails found."
    except Exception as e:
        state["email_context"] = f"Could not fetch emails: {str(e)}"
    
    return state

async def fetch_calendar_context(state: AgentState, db) -> AgentState:
    """Fetch calendar events"""
    from ..services.calendar_service import CalendarService
    
    try:
        events = await CalendarService.get_events(state["user_id"], db, days_ahead=7)
        
        if events:
            event_text = "UPCOMING EVENTS:\n" + "\n".join([
                f"- {e.get('summary', 'Event')}: {e.get('start', 'TBD')}" for e in events[:5]
            ])
            state["calendar_context"] = event_text
        else:
            state["calendar_context"] = "No upcoming events."
    except Exception as e:
        state["calendar_context"] = f"Could not fetch calendar: {str(e)}"
    
    return state

async def fetch_all_context(state: AgentState, db) -> AgentState:
    """Fetch email and calendar context"""
    state = await fetch_email_context(state, db)
    state = await fetch_calendar_context(state, db)
    return state

async def update_memory(state: AgentState, db) -> AgentState:
    """Extract and store new memories from user input"""
    from ..services.memory_service import MemoryService
    
    await MemoryService.extract_facts(
        state["user_id"],
        state["input"],
        db,
        source="chat"
    )
    
    state["memory_context"] = await MemoryService.get_memory_context(state["user_id"], db)
    return state

async def draft_email(state: AgentState, db) -> AgentState:
    """Draft an email based on user request and memory"""
    from ..services.memory_service import MemoryService
    
    constraints = await MemoryService.get_constraint_context(state["user_id"], db)
    recent_context = state.get("email_context", "")
    
    prompt = f"""You are drafting an email based on this user request:
"{state["input"]}"

User's known constraints and preferences:
{constraints if constraints else "No specific constraints known."}

Recent email context:
{recent_context}

Draft a professional email. Return ONLY the email content with:
- Subject line (prefixed with "Subject: ")
- Body of the email

Do not include any explanations or conversational text."""

    llm = get_llm()
    response = await llm.ainvoke([HumanMessage(content=prompt)])
    
    state["draft_email"] = response.content
    return state

async def send_email(state: AgentState, db) -> AgentState:
    """Send the drafted email"""
    from ..services.gmail_service import GmailService
    import re
    
    draft = state.get("draft_email", "")
    if not draft:
        return state
    
    lines = draft.split("\n")
    subject = ""
    body = ""
    is_body = False
    
    for line in lines:
        if line.startswith("Subject:"):
            subject = line.replace("Subject:", "").strip()
        elif line.strip() == "":
            is_body = True
        elif is_body:
            body += line + "\n"
    
    if subject and body:
        recipient_match = re.search(r'to\s+([^\s]+@[^\s]+)', state["input"])
        to = recipient_match.group(1) if recipient_match else "recipient@example.com"
        
        try:
            message_id = await GmailService.send_email(
                state["user_id"], to, subject, body.strip(), db
            )
            state["response"] = f"Email sent successfully! Message ID: {message_id}"
        except Exception as e:
            state["response"] = f"Failed to send email: {str(e)}"
    else:
        state["response"] = "Could not parse email draft."
    
    return state

async def process_message(state: AgentState, db) -> AgentState:
    """Process user message with all context"""
    from ..services.memory_service import MemoryService
    
    memory_context = state.get("memory_context", "No prior context.")
    email_context = state.get("email_context", "")
    calendar_context = state.get("calendar_context", "")
    
    prompt = SYSTEM_PROMPT.format(
        memory_context=memory_context,
        email_context=email_context,
        calendar_context=calendar_context
    )
    
    messages_with_system = [SystemMessage(content=prompt)] + state["messages"]
    
    llm = get_llm()
    response = await llm.ainvoke(messages_with_system)
    
    state["response"] = response.content
    state["messages"].append(AIMessage(content=response.content))
    
    return state

def should_fetch_context(state: AgentState) -> str:
    """Router: decide if we need to fetch context"""
    if state.get("needs_email_read") or state.get("needs_email_send"):
        return "fetch_context"
    return "skip_context"

def should_update_memory(state: AgentState) -> str:
    """Router: decide if we need to update memory"""
    if state.get("needs_memory_update"):
        return "update_memory"
    return "skip_memory"

def should_send_email(state: AgentState) -> str:
    """Router: decide if we need to send email"""
    if state.get("needs_email_send"):
        return "send_email"
    return "skip_send"

def build_agent_graph(db_session):
    """Build the agent graph with proper dependencies"""
    
    def create_graph():
        workflow = StateGraph(AgentState)
        
        workflow.add_node("analyze_intent", analyze_intent)
        workflow.add_node("fetch_context", lambda s: fetch_all_context(s, db_session))
        workflow.add_node("update_memory", lambda s: update_memory(s, db_session))
        workflow.add_node("draft_email", lambda s: draft_email(s, db_session))
        workflow.add_node("send_email", lambda s: send_email(s, db_session))
        workflow.add_node("process_message", lambda s: process_message(s, db_session))
        
        workflow.set_entry_point("analyze_intent")
        
        workflow.add_conditional_edges(
            "analyze_intent",
            should_fetch_context,
            {"fetch_context": "fetch_context", "skip_context": "update_memory"}
        )
        
        workflow.add_conditional_edges(
            "fetch_context",
            should_update_memory,
            {"update_memory": "update_memory", "skip_memory": "draft_email"}
        )
        
        workflow.add_conditional_edges(
            "update_memory",
            should_update_memory,
            {"update_memory": "update_memory", "skip_memory": "draft_email"}
        )
        
        workflow.add_conditional_edges(
            "draft_email",
            should_send_email,
            {"send_email": "send_email", "skip_send": "process_message"}
        )
        
        workflow.add_conditional_edges(
            "send_email",
            should_send_email,
            {"send_email": "send_email", "skip_send": "process_message"}
        )
        
        workflow.add_edge("process_message", END)
        
        return workflow.compile()
    
    return create_graph

# Simple agent function for direct calls
async def run_agent(user_id: str, message: str, db):
    """Run the agent with the given message"""
    from ..services.memory_service import MemoryService
    from ..services.gmail_service import GmailService
    from ..services.calendar_service import CalendarService
    
    memory_context = await MemoryService.get_memory_context(user_id, db)
    
    input_lower = message.lower()
    needs_email = any(w in input_lower for w in ["email", "inbox", "calendar", "meeting", "schedule"])
    
    email_context = ""
    calendar_context = ""
    
    if needs_email:
        try:
            emails = await GmailService.get_inbox(user_id, db, max_results=3)
            if emails:
                email_context = "RECENT EMAILS:\n" + "\n".join([
                    f"- {e['subject']} from {e['from']}" for e in emails[:3]
                ])
        except:
            pass
        
        try:
            events = await CalendarService.get_events(user_id, db, days_ahead=3)
            if events:
                calendar_context = "UPCOMING:\n" + "\n".join([
                    f"- {e.get('summary', 'Event')}: {e.get('start', 'TBD')}" for e in events[:3]
                ])
        except:
            pass
    
    needs_memory = any(w in input_lower for w in ["prefer", "don't like", "remember", "always", "never", "important"])
    
    if needs_memory:
        await MemoryService.extract_facts(user_id, message, db, source="chat")
        memory_context = await MemoryService.get_memory_context(user_id, db)
    
    prompt = SYSTEM_PROMPT.format(
        memory_context=memory_context or "No prior context.",
        email_context=email_context or "Not asked about email.",
        calendar_context=calendar_context or "Not asked about calendar."
    )
    
    llm = get_llm()
    response = await llm.ainvoke([SystemMessage(content=prompt), HumanMessage(content=message)])
    
    return response.content
