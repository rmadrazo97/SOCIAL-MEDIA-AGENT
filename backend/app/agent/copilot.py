"""Social Media Co-Pilot agent — LangGraph agent with CopilotKit integration."""
import json
import logging
from typing import List

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, ToolMessage, HumanMessage
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


def _extract_images_from_tool_messages(messages: list) -> list:
    """Scan tool messages for base64 images and convert them to multimodal content.

    When analyze_post_media returns images_base64, we inject them as a multimodal
    HumanMessage so the vision LLM can actually see the images.
    """
    enhanced = []
    for msg in messages:
        enhanced.append(msg)
        # Check if this is a ToolMessage with base64 images
        if isinstance(msg, ToolMessage):
            try:
                data = json.loads(msg.content) if isinstance(msg.content, str) else msg.content
                images = data.get("images_base64", []) if isinstance(data, dict) else []
                if images:
                    # Build multimodal content blocks
                    content_blocks = [
                        {"type": "text", "text": f"Here are the {len(images)} image(s) from this post for visual analysis:"}
                    ]
                    for img in images:
                        content_blocks.append({
                            "type": "image_url",
                            "image_url": {"url": img["data_url"]},
                        })
                    enhanced.append(HumanMessage(content=content_blocks))
                    # Remove base64 from tool message to save tokens
                    data_clean = {k: v for k, v in data.items() if k != "images_base64"}
                    data_clean["images_injected"] = True
                    msg.content = json.dumps(data_clean)
            except (json.JSONDecodeError, TypeError, KeyError):
                pass
    return enhanced


def _strip_reasoning_content(messages: list) -> list:
    """Strip reasoning_content from AI messages to avoid Kimi API errors.

    kimi-k2.5 returns reasoning_content with thinking enabled, but LangChain
    doesn't preserve it properly on replay, causing 400 errors. We strip it
    and disable thinking mode instead.
    """
    from langchain_core.messages import AIMessage, AIMessageChunk
    cleaned = []
    for msg in messages:
        if isinstance(msg, (AIMessage, AIMessageChunk)):
            # Remove reasoning_content from additional_kwargs if present
            if msg.additional_kwargs.get("reasoning_content"):
                msg = msg.model_copy()
                msg.additional_kwargs = {
                    k: v for k, v in msg.additional_kwargs.items()
                    if k != "reasoning_content"
                }
        cleaned.append(msg)
    return cleaned


async def chat_node(state: AgentState, config: RunnableConfig) -> Command[Literal["tool_node", "__end__"]]:
    """Main chat node — invokes the LLM with tools bound."""
    llm = ChatOpenAI(
        base_url="https://api.moonshot.ai/v1",
        api_key=settings.MOONSHOT_API_KEY or "dummy-key",
        model="kimi-k2.5",
        temperature=0.6,
        streaming=True,
        extra_body={"thinking": {"type": "disabled"}},
    )

    # Include any frontend-registered CopilotKit actions as tools
    copilotkit_actions = state.get("copilotkit", {}).get("actions", [])
    model_with_tools = llm.bind_tools([*all_tools, *copilotkit_actions])

    # Extract base64 images from tool results and inject as multimodal messages
    messages = _extract_images_from_tool_messages(state["messages"])
    # Strip reasoning_content from prior AI messages to prevent Kimi API errors
    messages = _strip_reasoning_content(messages)

    response = await model_with_tools.ainvoke(
        [SystemMessage(content=SYSTEM_PROMPT), *messages],
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
