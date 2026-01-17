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
4. If the user tells you something important (preferences, facts), use the 'save_memory' tool.
5. MANDATORY EMAIL DRAFTING RULE:
   - You are STRICTLY FORBIDDEN from calling 'draft_and_send_email' until the user has explicitly seen and approved a draft.
   - First, search for context if needed.
   - Then, provide a draft in your message text formatted clearly with 'To:', 'Subject:', and 'Body:'.
   - Only after the user says "Yes", "Send it", or "Go ahead", you can call 'draft_and_send_email'.
   - FAILURE TO SHOW A DRAFT FIRST IS A CRITICAL VIOLATION.
6. For Replies:
   - When the user asks to "Reply", use 'search_emails' to find the 'thread_id' of the original email.
   - Pass that 'thread_id' to 'draft_and_send_email' to ensure it's a proper reply and not a new email.
7. For Calendar:
   - MANDATORY APPROVAL RULE: You must propose the event details (Title, Date, and specific Time) to the user first.
   - Format it clearly: "I will create a calendar event for [Title] on [Date] at [Time]. Should I go ahead?"
   - DO NOT call 'create_calendar_event' until the user gives explicit approval.
   - Use the current time context to calculate relative dates (like "tomorrow").
   - Ensure you use ISO 8601 format (YYYY-MM-DDTHH:MM:SSZ) when calling the tool.
8. Be concise, professional, and proactive.

Current Time Context:
{time_context}

If you need to perform an action (read email, check calendar, save memory), use the appropriate tool.
"""

# --- Tools (Schema only for LLM) ---

@tool
def search_emails(query: str):
    """Search for relevant emails in the user's inbox. Provides snippets and subjects."""
    pass

@tool
def get_calendar_events(days: int = 7):
    """Get the user's upcoming calendar events. Specify number of days ahead (default 7)."""
    pass

@tool
def search_memory(query: str):
    """Search through long-term memory for relevant facts, preferences, and personal knowledge about the user."""
    pass

@tool
def save_memory(fact: str):
    """Save an important fact, preference, or piece of information about the user to their long-term memory."""
    pass

@tool
def draft_and_send_email(recipient: str, subject: str, body: str, thread_id: str = None):
    """Draft and send an email to a recipient. Use professional tone.
    If this is a reply, YOU MUST provide the thread_id of the original email."""
    pass

@tool
def create_calendar_event(title: str, start_time: str, end_time: str, description: str = "", location: str = ""):
    """Create a new calendar event. 
    Times must be in ISO format (YYYY-MM-DDTHH:MM:SSZ). 
    IMPORTANT: Always confirm free time first using get_calendar_events.
    """
    pass

# Define the tools list for the LLM
tools = [search_emails, get_calendar_events, search_memory, save_memory, draft_and_send_email, create_calendar_event]
llm_with_tools = get_llm().bind_tools(tools)

# --- Nodes ---

async def call_model(state: AgentState):
    """Call the LLM with current messages and context"""
    memory_context = await MemoryService.get_memory_context(state["user_id"], state["db"])
    
    from datetime import datetime
    time_context = f"Current server time is {datetime.now().strftime('%A, %Y-%m-%d %H:%M:%S')}. User is likely in IST (UTC+5:30) based on location."
    
    prompt = SYSTEM_PROMPT.format(memory_context=memory_context, time_context=time_context)
    messages = [SystemMessage(content=prompt)] + state["messages"]
    
    response = await llm_with_tools.ainvoke(messages)
    return {"messages": [response]}

async def execute_tools(state: AgentState):
    """Execute tools requested by the LLM using the actual services"""
    last_message = state["messages"][-1]
    tool_messages = []
    
    for tool_call in last_message.tool_calls:
        tool_name = tool_call["name"]
        args = tool_call["args"]
        call_id = tool_call["id"]
        
        result = ""
        try:
            if tool_name == "search_emails":
                emails = await GmailService.get_inbox(state["user_id"], state["db"], max_results=5)
                if not emails:
                    result = "No emails found."
                else:
                    result = "RECENT EMAILS:\n" + "\n".join([
                        f"- From: {e['from']}\n  Subject: {e['subject']}\n  Snippet: {e['preview']}\n  ThreadID: {e['thread_id']}" 
                        for e in emails
                    ])
            
            elif tool_name == "get_calendar_events":
                days = args.get("days", 7)
                events = await CalendarService.get_events(state["user_id"], state["db"], days_ahead=days)
                if not events:
                    result = "No upcoming events found."
                else:
                    result = f"UPCOMING EVENTS (Next {days} days):\n" + "\n".join([
                        f"- {e.get('summary', 'Event')} at {e.get('start', 'TBD')}" for e in events
                    ])
            
            elif tool_name == "search_memory":
                query = args.get("query", "")
                facts = await MemoryService.retrieve_relevant_facts(state["user_id"], query, state["db"])
                if not facts:
                    result = "No relevant memories found."
                else:
                    result = "RELEVANT MEMORIES:\n" + "\n".join([f"• {f}" for f in facts])
            
            elif tool_name == "save_memory":
                fact = args.get("fact", "")
                # Real storage
                await MemoryService.store_fact(state["user_id"], fact, "personal", 0.5, {}, state["db"])
                result = f"Successfully saved to memory: {fact}"
            
            elif tool_name == "draft_and_send_email":
                target = args.get("recipient")
                sub = args.get("subject", "No Subject")
                content = args.get("body", "")
                tid = args.get("thread_id")
                msg_id = await GmailService.send_email(state["user_id"], target, sub, content, state["db"], thread_id=tid)
                result = f"Email sent successfully to {target}! Message ID: {msg_id}"
            
            elif tool_name == "create_calendar_event":
                title = args.get("title")
                start = args.get("start_time")
                end = args.get("end_time")
                desc = args.get("description", "")
                loc = args.get("location", "")
                
                event_id = await CalendarService.create_event(
                    state["user_id"], title, start, end, desc, loc, state["db"]
                )
                result = f"Successfully created calendar event: {title} (ID: {event_id})"
            
            else:
                result = f"Unsupported tool: {tool_name}"
                
        except Exception as e:
            result = f"Error executing {tool_name}: {str(e)}"
            
        tool_messages.append(ToolMessage(content=result, tool_call_id=call_id, name=tool_name))
    
    return {"messages": tool_messages}

def should_continue(state: AgentState):
    """Determine if we should continue the loop or end"""
    messages = state["messages"]
    last_message = messages[-1]
    
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    return END

def build_agent_graph():
    """Build the LangGraph for the ReAct agent"""
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

async def run_agent(user_id: str, input_message: str, db: Any, conversation_history: list = None):
    """Run the agent and return the final response"""
    graph = build_agent_graph()
    
    messages = []
    if conversation_history:
        for msg in conversation_history:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(AIMessage(content=msg["content"]))
    else:
        messages = [HumanMessage(content=input_message)]
    
    initial_state = {
        "user_id": user_id,
        "messages": messages,
        "memory_context": "",
        "email_context": "",
        "calendar_context": "",
        "db": db
    }
    
    result = await graph.ainvoke(initial_state)
    
    ai_messages = [m for m in result["messages"] if isinstance(m, AIMessage)]
    if ai_messages:
        return ai_messages[-1].content
    return "I'm sorry, I couldn't process your request."
