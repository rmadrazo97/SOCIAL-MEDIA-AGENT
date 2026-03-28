"""CopilotKit agent endpoint — registers the Co-Pilot via CopilotKit Python SDK."""
import logging

logger = logging.getLogger(__name__)


def register_copilotkit(app):
    """Register CopilotKit endpoint on the FastAPI app."""
    try:
        from copilotkit import CopilotKitRemoteEndpoint
        from copilotkit.langgraph_agent import LangGraphAgent
        from copilotkit.integrations.fastapi import add_fastapi_endpoint
        from app.agent.copilot import get_copilot_graph

        graph = get_copilot_graph()

        agent = LangGraphAgent(
            name="social_media_copilot",
            description="Social Media Co-Pilot — helps creators analyze data, plan content, and grow their accounts.",
            graph=graph,
        )

        # CopilotKitRemoteEndpoint validates isinstance(agent, LangGraphAgent) and
        # rejects it (bug in copilotkit v0.1.83 — it forces LangGraphAGUIAgent which
        # is missing the execute() method). Bypass by setting agents after init.
        sdk = CopilotKitRemoteEndpoint(agents=[])
        sdk.agents = [agent]

        add_fastapi_endpoint(
            fastapi_app=app,
            sdk=sdk,
            prefix="/copilotkit",
        )

        logger.info("CopilotKit endpoint registered at /copilotkit")

    except ImportError as e:
        logger.warning("CopilotKit dependencies not installed, co-pilot disabled: %s", e)
    except Exception as e:
        logger.error("Failed to register CopilotKit endpoint: %s", e, exc_info=True)
