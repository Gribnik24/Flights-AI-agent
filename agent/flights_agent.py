import os
from dotenv import load_dotenv
from pathlib import Path

from langchain_openrouter import ChatOpenRouter
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, MessagesState, START, END
from langchain_core.messages import SystemMessage
from langgraph.prebuilt import ToolNode

from agent.tools import tools_list

load_dotenv()
_PROMPTS_DIR = Path(__file__).parent.parent / os.getenv("PROMPTS_DIR", "prompts")

if not os.path.exists("../logs"):
    os.makedirs("../logs")

MODEL_NAME = os.getenv('MODEL_NAME')
MODEL_API_BASE = os.getenv('MODEL_API_BASE')
MODEL_API_KEY = os.getenv('MODEL_API_KEY')

llm = ChatOpenRouter(model=MODEL_NAME, api_key=MODEL_API_KEY, base_url=MODEL_API_BASE, temperature=0)
memory = MemorySaver()

def make_agent_node(system_prompt: str, tools_list: list):
    """Create an agent node function that calls the LLM with bound tools."""
    llm_with_tools = llm.bind_tools(tools_list, parallel_tool_calls=True)

    def agent_node(state: MessagesState) -> dict:
        messages = [SystemMessage(content=system_prompt)] + state["messages"]
        response = llm_with_tools.invoke(messages)
        return {"messages": [response]}

    return agent_node

def route_after_agent(state: MessagesState) -> str:
    """Route to tools if the last message has tool calls, otherwise end."""
    last = state["messages"][-1]
    if hasattr(last, "tool_calls") and last.tool_calls:
        return "tools"
    return END

def build_graph():
    path = _PROMPTS_DIR / os.getenv("SYSTEM_PROMPT_PATH")
    system_prompt = path.read_text(encoding="utf-8")
    
    builder = StateGraph(MessagesState)
    builder.add_node("agent", make_agent_node(system_prompt, tools_list))
    builder.add_node("tools", ToolNode(tools_list))
    
    builder.add_edge(START, "agent")
    builder.add_conditional_edges("agent", route_after_agent)
    builder.add_edge("tools", "agent")
    
    return builder.compile(checkpointer=memory)

agent = build_graph()