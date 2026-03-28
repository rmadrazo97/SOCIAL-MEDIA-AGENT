"""Social Media Co-Pilot agent — LangGraph agent with CopilotKit integration."""
import logging
from typing import List

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command
from typing_extensions import Literal

from copilotkit import CopilotKitState

from app.agent.tools import all_tools
from app.agent.prompts.system import SYSTEM_PROMPT
from app.config import settings

logger = logging.getLogger(__name__)


class AgentState(CopilotKitState):
    """Agent state extending CopilotKit's base state."""
    pass


async def chat_node(state: AgentState, config: RunnableConfig) -> Command[Literal["tool_node", "__end__"]]:
    """Main chat node — invokes the LLM with tools bound."""
    llm = ChatOpenAI(
        base_url="https://api.moonshot.ai/v1",
        api_key=settings.MOONSHOT_API_KEY or "dummy-key",
        model="moonshot-v1-8k",
        temperature=0.3,
        streaming=True,
    )

    # Include any frontend-registered CopilotKit actions as tools
    copilotkit_actions = state.get("copilotkit", {}).get("actions", [])
    model_with_tools = llm.bind_tools([*all_tools, *copilotkit_actions])

    response = await model_with_tools.ainvoke(
        [SystemMessage(content=SYSTEM_PROMPT), *state["messages"]],
        config,
    )

    if response.tool_calls:
        return Command(goto="tool_node", update={"messages": response})
    return Command(goto="__end__", update={"messages": response})


def create_copilot_graph():
    """Create the compiled LangGraph for the Co-Pilot."""
    workflow = StateGraph(AgentState)

    workflow.add_node("chat_node", chat_node)
    workflow.add_node("tool_node", ToolNode(tools=all_tools))

    workflow.set_entry_point("chat_node")
    workflow.add_edge("tool_node", "chat_node")

    graph = workflow.compile(checkpointer=MemorySaver())
    logger.info("Co-Pilot graph compiled with %d tools", len(all_tools))
    return graph


# Lazy singleton
_graph = None


def get_copilot_graph():
    """Get or create the singleton Co-Pilot graph."""
    global _graph
    if _graph is None:
        _graph = create_copilot_graph()
    return _graph
