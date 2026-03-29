import {
  CopilotRuntime,
  copilotRuntimeNextJSAppRouterEndpoint,
  EmptyAdapter,
} from "@copilotkit/runtime";
import { LangGraphHttpAgent } from "@copilotkit/runtime/langgraph";

const BACKEND_URL = process.env.BACKEND_URL || "http://backend:8000";

const runtime = new CopilotRuntime({
  agents: {
    social_media_copilot: new LangGraphHttpAgent({
      url: `${BACKEND_URL}/copilotkit`,
    }),
  },
});

const serviceAdapter = new EmptyAdapter();

export const POST = async (req: Request) => {
  const { handleRequest } = copilotRuntimeNextJSAppRouterEndpoint({
    runtime,
    serviceAdapter,
    endpoint: "/api/copilotkit",
  });

  return handleRequest(req);
};
