from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolExecutor, ToolInvocation
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from typing import TypedDict, List, Any
import json
import os

class AgentState(TypedDict):
    """State for the agent"""
    user_id: str
    messages: List[Any]
    memory_context: str
    response: str

def get_llm():
    """Get LLM instance - lazily initialized"""
    return ChatGoogleGenerativeAI(
        model="gemini-1.5-pro",
        google_api_key=os.getenv("GOOGLE_API_KEY")
    )

def create_agent_graph():
    """Create the LangGraph agent workflow"""

    workflow = StateGraph(AgentState)

    # Define system prompt with memory context
    SYSTEM_PROMPT = """You are Chief of Staff AI Assistant - a personal agentic AI that helps with email, calendar, and task management.

You have access to:
- Email management (Gmail)
- Calendar management (Google Calendar)
- Task organization
- Dynamic memory of user preferences and facts

When responding:
1. Be concise and actionable
2. Proactively suggest next steps based on user context
3. Remember user preferences from the memory context
4. Use available tools to accomplish tasks

Current user context and memories:
{memory_context}"""

    async def process_message(state: AgentState) -> AgentState:
        """Process user message with Gemini"""
        memory_context = state.get("memory_context", "No prior context.")

        messages_with_system = [
            SystemMessage(content=SYSTEM_PROMPT.format(memory_context=memory_context))
        ] + state["messages"]

        llm = get_llm()
        response = await llm.ainvoke(messages_with_system)

        state["response"] = response.content
        state["messages"].append(AIMessage(content=response.content))

        return state

    async def extract_memory(state: AgentState) -> AgentState:
        """Extract facts from conversation for memory"""
        # For now, simple extraction - can be enhanced later
        last_user_message = None
        for msg in reversed(state["messages"]):
            if hasattr(msg, 'content') and isinstance(msg, HumanMessage):
                last_user_message = msg.content
                break

        # Return state as-is; actual extraction happens in memory service
        return state

    # Add nodes
    workflow.add_node("process", process_message)
    workflow.add_node("extract_memory", extract_memory)

    # Define flow
    workflow.set_entry_point("process")
    workflow.add_edge("process", "extract_memory")
    workflow.add_edge("extract_memory", END)

    return workflow.compile()

# Compile the graph
agent = create_agent_graph()
