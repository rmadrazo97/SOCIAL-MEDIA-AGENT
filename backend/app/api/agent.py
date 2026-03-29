"""CopilotKit agent endpoint — registers the Co-Pilot via CopilotKit Python SDK."""
import json
import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)

AGENT_NAME = "social_media_copilot"
AGENT_DESC = "Social Media Co-Pilot — helps creators analyze data, plan content, and grow their accounts."


class CopilotKitInfoMiddleware(BaseHTTPMiddleware):
    """
    Middleware that handles CopilotKit info discovery and transforms responses
    to the format expected by the frontend SDK v1.54+.
    """

    async def dispatch(self, request: Request, call_next):
        path = request.url.path.rstrip("/")

        # Handle GET /copilotkit/info — the SDK catch-all rejects GET without body
        if request.method == "GET" and path == "/copilotkit/info":
            return Response(
                content=json.dumps({
                    "agents": {AGENT_NAME: {"description": AGENT_DESC}},
                    "version": "0.1.83",
                }),
                status_code=200,
                media_type="application/json",
            )

        response = await call_next(request)

        # Transform POST /copilotkit info responses (array→object agents format)
        if request.method == "POST" and path == "/copilotkit":
            body_bytes = b""
            async for chunk in response.body_iterator:
                body_bytes += chunk.encode() if isinstance(chunk, str) else chunk
            try:
                data = json.loads(body_bytes)
                agents = data.get("agents", [])
                if isinstance(agents, list):
                    data["agents"] = {
                        a["name"]: {"description": a.get("description", "")}
                        for a in agents if isinstance(a, dict) and "name" in a
                    }
                if "sdkVersion" in data and "version" not in data:
                    data["version"] = data.pop("sdkVersion")
                return Response(content=json.dumps(data), status_code=response.status_code,
                                media_type="application/json")
            except (json.JSONDecodeError, UnicodeDecodeError):
                return Response(content=body_bytes, status_code=response.status_code,
                                headers=dict(response.headers), media_type=response.media_type)

        return response


def register_copilotkit(app):
    """Register CopilotKit endpoint on the FastAPI app."""
    app.add_middleware(CopilotKitInfoMiddleware)

    try:
        from copilotkit import CopilotKitRemoteEndpoint, LangGraphAGUIAgent
        from copilotkit.integrations.fastapi import add_fastapi_endpoint
        from ag_ui_langgraph import add_langgraph_fastapi_endpoint
        from app.agent.copilot import get_copilot_graph

        graph = get_copilot_graph()

        # Create AG-UI agent for actual execution
        agui_agent = LangGraphAGUIAgent(
            name=AGENT_NAME,
            description=AGENT_DESC,
            graph=graph,
        )

        # Register the AG-UI run endpoint BEFORE the CopilotKit catch-all.
        # The frontend SDK sends POST /copilotkit/agent/{name}/run for execution.
        add_langgraph_fastapi_endpoint(
            app,
            agui_agent,
            path=f"/copilotkit/agent/{AGENT_NAME}/run",
        )

        # Also register for /connect (used for reconnection)
        add_langgraph_fastapi_endpoint(
            app,
            agui_agent,
            path=f"/copilotkit/agent/{AGENT_NAME}/connect",
        )

        # Register CopilotKit SDK catch-all for info/state/other endpoints.
        # Use LangGraphAgent for the SDK's own routing (info, state, etc.)
        from copilotkit.langgraph_agent import LangGraphAgent
        legacy_agent = LangGraphAgent(
            name=AGENT_NAME,
            description=AGENT_DESC,
            graph=graph,
        )
        sdk = CopilotKitRemoteEndpoint(agents=[])
        sdk.agents = [legacy_agent]

        add_fastapi_endpoint(
            fastapi_app=app,
            sdk=sdk,
            prefix="/copilotkit",
        )

        logger.info("CopilotKit endpoint registered at /copilotkit (AG-UI + legacy)")

    except ImportError as e:
        logger.warning("CopilotKit dependencies not installed, co-pilot disabled: %s", e)
    except Exception as e:
        logger.error("Failed to register CopilotKit endpoint: %s", e, exc_info=True)
