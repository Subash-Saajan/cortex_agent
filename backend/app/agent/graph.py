from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from typing import TypedDict, List, Any, Annotated, Union
import json
import os
import operator
from langchain_core.tools import tool
from ..services.memory_service import MemoryService
from ..services.gmail_service import GmailService
from ..services.calendar_service import CalendarService

class AgentState(TypedDict):
    """State for the agent"""
    user_id: str
    messages: Annotated[List[Union[HumanMessage, AIMessage, SystemMessage, ToolMessage]], operator.add]
    memory_context: str
    email_context: str
    calendar_context: str
    db: Any # Database session

def get_llm():
    """Get LLM instance with tool support"""
    return ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        google_api_key=os.getenv("GOOGLE_API_KEY"),
        temperature=0
    )

SYSTEM_PROMPT = """You are Cortex, a personal AI Chief of Staff.
You help the user manage their life by accessing their email, calendar, and long-term memory.

Current Context:
{memory_context}

Guidelines:
1. Always check the calendar for schedule-related questions.
2. Search through emails for information about projects, people, or events.
3. Use your memory to provide personalized responses based on user preferences.
4. If the user tells you something important (preferences, facts), use the 'update_memory' tool.
5. When drafting emails, follow the user's style and constraints from memory.
6. Be concise, professional, and proactive.

If you need to perform an action (read email, check calendar, save memory), use the appropriate tool.
"""

# --- Tools ---

@tool
async def search_emails(query: str, state: AgentState) -> str:
    """Search for relevant emails in the user's inbox."""
    try:
        emails = await GmailService.get_inbox(state["user_id"], state["db"], max_results=5)
        if not emails:
            return "No emails found in the inbox."
        
        email_text = "RECENT EMAILS:\n" + "\n".join([
            f"- From: {e['from']}\n  Subject: {e['subject']}\n  Snippet: {e['preview']}" 
            for e in emails
        ])
        return email_text
    except Exception as e:
        return f"Error searching emails: {str(e)}"

@tool
async def get_calendar_events(days: int = 7, state: AgentState = None) -> str:
    """Get the user's upcoming calendar events."""
    try:
        events = await CalendarService.get_events(state["user_id"], state["db"], days_ahead=days)
        if not events:
            return "No upcoming events found."
        
        event_text = f"UPCOMING EVENTS (Next {days} days):\n" + "\n".join([
            f"- {e['title']} at {e['start']}" for e in events
        ])
        return event_text
    except Exception as e:
        return f"Error fetching calendar: {str(e)}"

@tool
async def search_memory(query: str, state: Annotated[AgentState, "state"]) -> str:
    """Search through long-term memory for relevant facts about the user."""
    try:
        facts = await MemoryService.retrieve_relevant_facts(state["user_id"], query, state["db"])
        if not facts:
            return "No relevant memories found."
        return "RELEVANT MEMORIES:\n" + "\n".join([f"• {f}" for f in facts])
    except Exception as e:
        return f"Error searching memory: {str(e)}"

@tool
async def save_memory(fact: str, category: str, importance: float = 0.5) -> str:
    """Save an important fact or preference about the user to long-term memory."""
    # This will be handled by the memory extraction service if called
    return f"I will remember that: {fact}"

@tool
async def draft_and_send_email(recipient: str, subject: str, body: str, state: AgentState) -> str:
    """Draft and send an email to a recipient."""
    try:
        message_id = await GmailService.send_email(
            state["user_id"], recipient, subject, body, state["db"]
        )
        return f"Email sent successfully! Message ID: {message_id}"
    except Exception as e:
        return f"Failed to send email: {str(e)}"

# Define the tools list for the LLM
tools = [search_emails, get_calendar_events, search_memory, save_memory, draft_and_send_email]
llm_with_tools = get_llm().bind_tools(tools)

# --- Nodes ---

async def call_model(state: AgentState):
    """Call the LLM with current messages and context"""
    memory_context = await MemoryService.get_memory_context(state["user_id"], state["db"])
    
    prompt = SYSTEM_PROMPT.format(memory_context=memory_context)
    messages = [SystemMessage(content=prompt)] + state["messages"]
    
    response = await llm_with_tools.ainvoke(messages)
    return {"messages": [response]}

async def execute_tools(state: AgentState):
    """Execute tools requested by the LLM"""
    last_message = state["messages"][-1]
    tool_messages = []
    
    for tool_call in last_message.tool_calls:
        tool_name = tool_call["name"]
        args = tool_call["args"]
        
        # Inject state into tools if they need it
        if tool_name == "search_emails":
            result = await search_emails.ainvoke({"query": args.get("query", ""), "state": state})
        elif tool_name == "get_calendar_events":
            result = await get_calendar_events.ainvoke({"days": args.get("days", 7), "state": state})
        elif tool_name == "search_memory":
            result = await search_memory.ainvoke({"query": args.get("query", ""), "state": state})
        elif tool_name == "draft_and_send_email":
            result = await draft_and_send_email.ainvoke({
                "recipient": args.get("recipient"),
                "subject": args.get("subject"),
                "body": args.get("body"),
                "state": state
            })
        elif tool_name == "save_memory":
            # Real extraction happens here
            await MemoryService.store_fact(
                state["user_id"], 
                args.get("fact"), 
                args.get("category", "personal"), 
                args.get("importance", 0.5), 
                {}, 
                state["db"]
            )
            result = f"Stored memory: {args.get('fact')}"
        else:
            result = f"Tool {tool_name} not found."
            
        tool_messages.append(ToolMessage(
            tool_call_id=tool_call["id"],
            content=str(result)
        ))
        
    return {"messages": tool_messages}

def should_continue(state: AgentState):
    """Determine whether to continue the loop or end"""
    messages = state["messages"]
    last_message = messages[-1]
    
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    return END

# --- Graph Building ---

def build_agent_graph(db_session):
    """Build the ReAct agent graph"""
    
    workflow = StateGraph(AgentState)
    
    workflow.add_node("agent", call_model)
    workflow.add_node("tools", execute_tools)
    
    workflow.set_entry_point("agent")
    
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            END: END
        }
    )
    
    workflow.add_edge("tools", "agent")
    
    return workflow.compile()

async def run_agent(user_id: str, message: str, db):
    """Run the agent and return the final response"""
    app = build_agent_graph(db)
    
    inputs = {
        "user_id": user_id,
        "messages": [HumanMessage(content=message)],
        "db": db
    }
    
    final_state = await app.ainvoke(inputs)
    
    # Extract the final AI response
    for msg in reversed(final_state["messages"]):
        if isinstance(msg, AIMessage) and msg.content:
            return msg.content
            
    return "I'm sorry, I couldn't process that request."

