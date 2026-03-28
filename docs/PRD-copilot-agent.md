# PRD: Social Media Co-Pilot Agent

**Version**: 1.0
**Date**: 2026-03-28
**Status**: Draft
**Author**: AI-assisted

---

## 1. Overview

### 1.1 Problem Statement

The Social Media Command Center currently provides data scraping, baseline computation, and batch AI-generated briefs/recommendations via scheduled jobs. The creator must navigate between dashboards, manually trigger syncs, and interpret static reports. There is no conversational interface for the creator to ask questions, explore data interactively, or receive proactive, context-aware guidance that evolves with their account growth.

### 1.2 Vision

Build a **Co-Pilot Agent** — a persistent, memory-equipped conversational assistant embedded in the platform as a floating chat widget. The agent understands the creator's accounts, content history, engagement patterns, and goals. It grows alongside the creator, learning preferences and refining recommendations over time. It can autonomously execute backend queries, generate reports, suggest content, analyze trends, and produce actionable artifacts — all through natural conversation.

### 1.3 Key Principles

- **Relationship-first**: The agent builds a long-term understanding of the creator — their voice, niche, audience, goals, and content style
- **Action-oriented**: Not just Q&A — the agent executes queries, creates artifacts, and triggers workflows
- **Progressive intelligence**: Memory and context accumulate over time, making recommendations increasingly personalized
- **Native integration**: The agent operates through the existing API, not as a sidecar — it reads and writes the same data the dashboard displays

---

## 2. Technology Stack

### 2.1 Agent Framework: LangChain Deep Agents

**Package**: `deepagents` ([docs](https://docs.langchain.com/oss/python/deepagents/overview))

Deep Agents provide the core agent harness with built-in capabilities that map directly to the co-pilot's needs:

| Deep Agents Feature | Co-Pilot Use |
|---------------------|-------------|
| **Planning Tool** (`write_todos`) | Decompose complex requests (e.g., "build me a content strategy for next week") into tracked steps |
| **Filesystem Tools** | Store and retrieve generated artifacts (reports, strategies, content drafts) in the agent's virtual filesystem |
| **Subagent Spawning** (`task` tool) | Delegate specialized work — one subagent for trend analysis, another for content generation — with context isolation |
| **Long-term Memory** (LangGraph Memory Store) | Persist creator preferences, past interactions, learned patterns across sessions |

**LLM Backend**: Moonshot/Kimi API (`moonshot-v1-8k`) via the existing OpenAI-compatible client at `https://api.moonshot.ai/v1` — reusing the `MOONSHOT_API_KEY` already configured in the project.

### 2.2 Frontend UI: CopilotKit + AG-UI Protocol

**Packages**:
- `@copilotkit/react-core` — hooks and state management
- `@copilotkit/react-ui` — `CopilotPopup` floating chat component
- `@copilotkit/runtime` — Next.js API route runtime (bridges frontend to agent)

**Protocol**: [AG-UI](https://docs.ag-ui.com/) (Agent-User Interaction Protocol) — the open, event-based protocol that enables real-time streaming between the agent backend and the chat UI. Key event types used:

- **Lifecycle**: `RunStarted` / `RunFinished` / `RunError` for run tracking
- **Text Message Streaming**: `TextMessageStart` → `TextMessageContent` → `TextMessageEnd`
- **Tool Calls**: `ToolCallStart` → `ToolCallArgs` → `ToolCallEnd` → `ToolCallResult` (visible in UI as agent "actions")
- **State Sync**: `StateSnapshot` / `StateDelta` for shared state between agent and frontend
- **Activity Events**: Show intermediate work (e.g., "Analyzing 30-day engagement data...")

### 2.3 Integration Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Browser (Next.js 15)                      │
│                                                              │
│  ┌──────────────┐   ┌──────────────────────────────────┐    │
│  │  Dashboard    │   │  CopilotPopup (floating chat)    │    │
│  │  (existing)   │   │  @copilotkit/react-ui            │    │
│  └──────┬───────┘   └──────────────┬───────────────────┘    │
│         │                          │ AG-UI events            │
│         │                          ▼                         │
│         │            ┌─────────────────────────┐             │
│         │            │ /api/copilotkit          │             │
│         │            │ CopilotKit Runtime       │             │
│         │            └────────────┬────────────┘             │
└─────────┼─────────────────────────┼──────────────────────────┘
          │                         │ HTTP / AG-UI stream
          ▼                         ▼
┌──────────────────┐  ┌──────────────────────────────────────┐
│  FastAPI (8001)  │◄─┤  Deep Agent Service (Python)         │
│  (existing API)  │  │                                      │
│                  │  │  ┌────────────┐  ┌────────────────┐  │
│  /api/accounts   │  │  │ Planning   │  │ Long-term      │  │
│  /api/posts      │  │  │ Tool       │  │ Memory Store   │  │
│  /api/metrics    │  │  │            │  │ (LangGraph)    │  │
│  /api/briefs     │  │  ├────────────┤  ├────────────────┤  │
│  /api/insights   │  │  │ API Tools  │  │ Artifact FS    │  │
│  /api/sync       │  │  │ (backend)  │  │ (virtual)      │  │
│  /api/remix      │  │  ├────────────┤  ├────────────────┤  │
│                  │  │  │ Subagents  │  │ Creator        │  │
│                  │  │  │ (analysis, │  │ Profile        │  │
│                  │  │  │  content)  │  │ Memory         │  │
│                  │  │  └────────────┘  └────────────────┘  │
└──────────────────┘  └──────────────────────────────────────┘
          │                         │
          ▼                         ▼
    ┌───────────┐          ┌──────────────┐
    │ PostgreSQL│          │ Redis        │
    │ (existing)│          │ (sessions +  │
    │           │          │  agent state)│
    └───────────┘          └──────────────┘
```

---

## 3. Agent Capabilities

### 3.1 Core Tool Set

The Deep Agent will be equipped with tools that map to existing backend API endpoints:

#### Data Query Tools

| Tool Name | Backend Endpoint | Description |
|-----------|-----------------|-------------|
| `get_accounts` | `GET /api/accounts` | List all tracked accounts with follower counts |
| `get_account_metrics` | `GET /api/metrics/account/{id}` | Aggregated metrics for an account |
| `get_account_baseline` | `GET /api/metrics/baselines/{id}` | 30-day performance baselines |
| `get_posts` | `GET /api/posts` | List posts with filters (account, date range, type) |
| `get_post_detail` | `GET /api/posts/{id}` | Post with latest metrics snapshot |
| `get_post_metrics_history` | `GET /api/posts/{id}/metrics` | Metric snapshots over time for trend analysis |
| `get_daily_brief` | `GET /api/briefs` | Fetch existing daily briefs |
| `get_recommendations` | `GET /api/recommendations` | Current pending recommendations |

#### Action Tools

| Tool Name | Backend Endpoint | Description |
|-----------|-----------------|-------------|
| `trigger_sync` | `POST /api/sync/all` | Refresh data from Instagram/TikTok |
| `trigger_baseline_recompute` | `POST /api/sync/baselines` | Recompute 30-day baselines |
| `generate_diagnostic` | `POST /api/insights/diagnostic` | AI diagnostic for a specific post |
| `generate_brief` | `POST /api/briefs/generate` | Generate daily brief on demand |
| `generate_remix` | `POST /api/remix` | Create content remix from existing post |
| `update_recommendation_status` | `PATCH /api/recommendations/{id}` | Accept or dismiss a recommendation |

#### Analysis Tools (New — Agent-native)

| Tool Name | Description |
|-----------|-------------|
| `analyze_engagement_trends` | Query metrics across posts, compute trends, identify patterns (rising/falling engagement, best performing content types) |
| `compare_time_periods` | Compare metrics between two date ranges (week-over-week, month-over-month) |
| `identify_top_content` | Rank posts by engagement rate, views, or growth relative to baseline |
| `analyze_posting_patterns` | Examine posting frequency, timing, and correlation with engagement |
| `analyze_audience_behavior` | Infer audience activity patterns from engagement timing data |
| `generate_content_ideas` | Produce content suggestions based on top performers, trends, and creator's niche |
| `generate_copy_draft` | Write caption/copy for a content idea, matching the creator's voice |
| `create_content_strategy` | Build a multi-day content plan with themes, formats, and timing |
| `create_report` | Generate a structured performance report (weekly, monthly, custom range) |

#### Artifact Management Tools

| Tool Name | Description |
|-----------|-------------|
| `save_artifact` | Persist a generated artifact (report, strategy, content idea) to the virtual filesystem and database |
| `list_artifacts` | List saved artifacts by type and date |
| `retrieve_artifact` | Load a previously saved artifact |

### 3.2 Memory Architecture

The agent's memory operates at three levels:

#### Level 1 — Session Memory (Conversation Context)
- Current conversation messages and tool call history
- Managed automatically by the Deep Agent's message state
- Cleared between sessions

#### Level 2 — Creator Profile Memory (Persistent)
- Stored in LangGraph Memory Store, keyed by creator account
- Accumulates over time from interactions:

```json
{
  "creator_profile": {
    "niche": "fitness & wellness",
    "content_style": "educational reels with humor",
    "voice_tone": "casual, motivational, Gen-Z slang",
    "goals": ["reach 100k followers by Q3", "monetize through brand deals"],
    "preferred_posting_times": ["9am EST", "7pm EST"],
    "audience_demographics_inferred": "18-34, US, fitness enthusiasts",
    "content_strengths": ["transformation stories", "quick tips"],
    "content_weaknesses": ["carousels underperform", "long captions get less engagement"],
    "topics_to_avoid": ["politics", "controversial diets"],
    "brand_partnerships_interest": ["supplement brands", "athleisure"],
    "interaction_preferences": {
      "detail_level": "concise",
      "prefers_data_backed": true,
      "likes_emoji_in_copy": true
    }
  }
}
```

#### Level 3 — Historical Knowledge Memory (Persistent)
- Key insights and learnings the agent has derived:
  - "Creator's reels about morning routines consistently outperform (2.3x baseline)"
  - "Engagement drops on weekends — audience is weekday-active"
  - "Creator rejected carousel suggestions twice — prefers video format"
  - "Hashtag strategy shifted from broad (#fitness) to niche (#5amworkoutclub) in Feb 2026"
- Used to avoid repeating rejected suggestions and to build on successful patterns

### 3.3 Artifact System

The agent produces structured outputs saved as **artifacts** — persistent, retrievable objects:

| Artifact Type | Description | Storage |
|---------------|-------------|---------|
| `content_idea` | Single content suggestion with format, topic, hook, and rationale | DB (new `Artifact` model) + agent filesystem |
| `copy_draft` | Written caption/script with variants | DB + agent filesystem |
| `content_strategy` | Multi-day plan with themes, formats, timing | DB + agent filesystem |
| `performance_report` | Period-based analysis with metrics, trends, insights | DB + agent filesystem |
| `trend_analysis` | Analysis of trending topics/formats relevant to creator's niche | DB + agent filesystem |
| `task` | Actionable to-do item the creator should execute | DB (new `Task` model) |
| `competitor_analysis` | Profile comparison with another account | Agent filesystem |

---

## 4. User Experience

### 4.1 Floating Chat Widget

The co-pilot appears as a floating button (bottom-right corner) on all dashboard pages using CopilotKit's `CopilotPopup` component. Clicking it opens a chat panel.

**Visual Design**:
- Background: `bg-ebony` (#414833)
- Text: `text-bone` (#EBE3D2)
- Accent: `bg-sage` (#A4AC86)
- Border: `border-dun` (#CCBFA3)
- Consistent with the existing dashboard theme

**Chat Features**:
- Streaming text responses (token-by-token via AG-UI `TextMessageContent` events)
- Visible tool execution (shows "Fetching your account metrics..." when tools run, via AG-UI `ToolCallStart` events)
- Activity indicators ("Analyzing 47 posts from the last 30 days...")
- Rich artifact rendering — strategies and reports render as structured cards, not raw text
- Suggested prompts / quick actions for common queries
- Conversation history (scrollable, persisted per session)

### 4.2 Example Interactions

**Quick Data Query**:
```
Creator: How did my reels perform this week?
Agent: [calls get_posts, get_account_baseline]
       Your reels this week averaged 12,400 views — 34% above your 30-day
       baseline of 9,250. Top performer: "Morning Routine Hack" (28.1K views,
       8.2% engagement rate). Your weakest reel was "Supplement Review" at
       4,100 views. Want me to analyze what made the top one work?
```

**Content Ideation**:
```
Creator: I need 3 content ideas for next week
Agent: [calls get_posts, analyze_engagement_trends, retrieves creator profile memory]
       Based on your top performers and current engagement trends:

       1. "5 AM Workout Challenge — Day 1" (Reel)
          Hook: "I tried waking up at 5am for a week..."
          Why: Your transformation/challenge content averages 2.1x baseline views

       2. "What I Eat in a Day — Honest Edition" (Reel)
          Hook: "No one shows the 10pm snack run..."
          Why: Authentic/relatable content drives your highest comment rates

       3. "3 Exercises You're Doing Wrong" (Carousel → Reel)
          Hook: Quick myth-busting with before/after form
          Why: Educational quick-tips are your second-best format

       Want me to draft captions for any of these?
       [saves as content_idea artifacts]
```

**Strategy Building**:
```
Creator: Build me a content strategy for April
Agent: [calls get_account_metrics, analyze_posting_patterns, analyze_engagement_trends]
       [spawns subagent for trend research]
       [retrieves creator profile + historical memory]

       📋 April Content Strategy (saved as artifact)

       Theme: "Spring Reset" — wellness refresh angle
       Cadence: 5 posts/week (Mon-Fri)
       Format Mix: 3 Reels, 1 Carousel, 1 Story series

       Week 1: Foundation
       - Mon: "Spring Reset Intro" Reel (hook + goals)
       - Tue: "Pantry Cleanout" Carousel (educational)
       ...

       [creates individual task artifacts for each post]
```

**Proactive Insights**:
```
Agent: I noticed your engagement rate dropped 18% over the last 5 posts.
       Looking at the data, all 5 were posted after 9pm — your audience
       typically engages most between 7-9am and 6-8pm EST. Want me to
       adjust your content calendar timing?
```

### 4.3 Suggested Quick Actions

The chat widget shows clickable prompt suggestions contextual to the current page:

| Dashboard Page | Suggested Prompts |
|----------------|-------------------|
| Main Dashboard | "Summarize my week", "What should I post today?", "Any alerts?" |
| Account Detail | "Analyze this account's trends", "Compare to last month" |
| Post Detail | "Why did this post perform well/poorly?", "Remix this content" |
| Recommendations | "Explain this recommendation", "Generate more ideas" |

---

## 5. Data Model Changes

### 5.1 New Models

#### Artifact

```python
class Artifact(Base):
    __tablename__ = "artifacts"

    id = Column(UUID, primary_key=True, default=uuid4)
    account_id = Column(UUID, ForeignKey("accounts.id", ondelete="CASCADE"))
    artifact_type = Column(String)  # content_idea, copy_draft, strategy, report, trend_analysis, task
    title = Column(String)
    content = Column(Text)  # markdown or structured text
    metadata_json = Column(JSONB)  # type-specific structured data
    status = Column(String, default="active")  # active, archived, completed (for tasks)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    account = relationship("Account", backref="artifacts")
```

#### AgentConversation

```python
class AgentConversation(Base):
    __tablename__ = "agent_conversations"

    id = Column(UUID, primary_key=True, default=uuid4)
    thread_id = Column(String, unique=True, index=True)  # LangGraph thread ID
    account_id = Column(UUID, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=True)
    summary = Column(Text, nullable=True)  # auto-generated conversation summary
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_active_at = Column(DateTime(timezone=True), server_default=func.now())
```

#### AgentMemoryEntry

```python
class AgentMemoryEntry(Base):
    __tablename__ = "agent_memory_entries"

    id = Column(UUID, primary_key=True, default=uuid4)
    account_id = Column(UUID, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=True)
    memory_type = Column(String)  # creator_profile, insight, preference, pattern
    key = Column(String, index=True)  # semantic key for retrieval
    content = Column(Text)
    confidence = Column(Numeric(3, 2), default=1.0)  # decay over time if not reinforced
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
```

### 5.2 Existing Model Usage

No changes to existing models. The agent reads/writes through the existing API, so `Post`, `PostMetric`, `Account`, `AccountBaseline`, `Insight`, `Recommendation`, and `DailyBrief` remain unchanged.

---

## 6. Backend Implementation

### 6.1 New Files

```
backend/app/
├── agent/
│   ├── __init__.py
│   ├── copilot.py              # Deep Agent definition (create_deep_agent)
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── query_tools.py      # Data query tools (get_accounts, get_posts, etc.)
│   │   ├── action_tools.py     # Action tools (trigger_sync, generate_brief, etc.)
│   │   ├── analysis_tools.py   # Analysis tools (trends, comparisons, patterns)
│   │   ├── content_tools.py    # Content generation tools (ideas, copy, strategy)
│   │   └── artifact_tools.py   # Artifact CRUD tools
│   ├── memory/
│   │   ├── __init__.py
│   │   ├── store.py            # LangGraph Memory Store configuration
│   │   └── creator_profile.py  # Creator profile memory management
│   ├── prompts/
│   │   ├── __init__.py
│   │   └── system.py           # System prompt with agent persona and instructions
│   └── config.py               # Agent-specific configuration
├── api/
│   ├── artifacts.py            # CRUD endpoints for artifacts
│   └── agent.py                # Agent conversation endpoints (if needed beyond CopilotKit)
```

### 6.2 Agent Definition (`agent/copilot.py`)

```python
from deepagents import create_deep_agent
from langchain_openai import ChatOpenAI

from app.agent.tools import (
    query_tools,
    action_tools,
    analysis_tools,
    content_tools,
    artifact_tools,
)
from app.agent.prompts.system import SYSTEM_PROMPT
from app.agent.memory.store import get_memory_store
from app.config import settings


def create_copilot_agent():
    """Create the Social Media Co-Pilot Deep Agent."""

    llm = ChatOpenAI(
        base_url="https://api.moonshot.ai/v1",
        api_key=settings.MOONSHOT_API_KEY,
        model="moonshot-v1-8k",
    )

    all_tools = [
        *query_tools,
        *action_tools,
        *analysis_tools,
        *content_tools,
        *artifact_tools,
    ]

    agent = create_deep_agent(
        model=llm,
        tools=all_tools,
        system_prompt=SYSTEM_PROMPT,
        # Deep Agent built-in features:
        # - Planning tool (write_todos) included automatically
        # - Filesystem tools included automatically
        # - Subagent spawning (task) included automatically
    )

    return agent
```

### 6.3 System Prompt (`agent/prompts/system.py`)

```python
SYSTEM_PROMPT = """You are the Social Media Co-Pilot — a personal AI assistant
for a content creator. You help them grow their social media presence by analyzing
their data, suggesting content, and providing actionable insights.

## Your Personality
- Supportive, encouraging, and direct
- Data-driven — always back suggestions with metrics when available
- Proactive — notice patterns and surface insights without being asked
- Adaptive — learn the creator's preferences and style over time

## Your Capabilities
- Query account data, posts, metrics, and baselines through the platform API
- Analyze engagement trends, posting patterns, and content performance
- Generate content ideas, captions, and strategies tailored to the creator
- Create and manage artifacts (reports, strategies, tasks, content ideas)
- Remember the creator's preferences, goals, and past interactions

## Guidelines
- When analyzing data, always compare against the 30-day baseline
- Frame metrics in relative terms ("34% above your average") not just absolutes
- When suggesting content, explain WHY based on data patterns
- Keep responses concise unless the creator asks for detail
- Save important artifacts so they can be referenced later
- Update your understanding of the creator after each meaningful interaction

## Memory Usage
- Check creator profile memory at the start of each conversation
- Update memory when you learn new preferences, goals, or patterns
- Reference past interactions when relevant ("Last week you mentioned...")
- Track which suggestions were accepted/rejected to refine future recommendations
"""
```

### 6.4 Tool Example (`agent/tools/query_tools.py`)

```python
import httpx
from langchain_core.tools import tool
from app.config import settings


BACKEND_BASE = "http://localhost:8001"
HEADERS = {"X-App-Password": settings.APP_PASSWORD}


@tool
def get_accounts() -> str:
    """Get all tracked social media accounts with their follower counts and status."""
    response = httpx.get(f"{BACKEND_BASE}/api/accounts", headers=HEADERS)
    return response.json()


@tool
def get_account_metrics(account_id: str) -> str:
    """Get aggregated engagement metrics for a specific account.

    Args:
        account_id: UUID of the account to query
    """
    response = httpx.get(
        f"{BACKEND_BASE}/api/metrics/account/{account_id}",
        headers=HEADERS,
    )
    return response.json()


@tool
def get_posts(account_id: str = None, post_type: str = None, limit: int = 20) -> str:
    """Get posts with optional filters.

    Args:
        account_id: Filter by account UUID (optional)
        post_type: Filter by type: image, carousel, reel, video (optional)
        limit: Max posts to return (default 20)
    """
    params = {"limit": limit}
    if account_id:
        params["account_id"] = account_id
    if post_type:
        params["post_type"] = post_type
    response = httpx.get(
        f"{BACKEND_BASE}/api/posts", headers=HEADERS, params=params
    )
    return response.json()
```

### 6.5 CopilotKit Runtime Integration

The agent is exposed to the frontend via a CopilotKit runtime endpoint in the Next.js API route:

```typescript
// frontend/src/app/api/copilotkit/route.ts
import {
  CopilotRuntime,
  LangGraphAdapter,
} from "@copilotkit/runtime";

const runtime = new CopilotRuntime({
  remoteEndpoints: [
    {
      url: "http://backend:8001/api/agent/stream",
      // LangGraph-compatible endpoint served by the Deep Agent
    },
  ],
});

export const POST = async (req: Request) => {
  const { handleRequest } = runtime;
  return handleRequest(req);
};
```

Alternatively, the Deep Agent can expose an AG-UI compatible endpoint directly from FastAPI:

```python
# backend/app/api/agent.py
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from ag_ui.fastapi import ag_ui_endpoint

from app.agent.copilot import create_copilot_agent

router = APIRouter(prefix="/api/agent", tags=["agent"])

agent = create_copilot_agent()

@router.post("/stream")
@ag_ui_endpoint
async def stream(request):
    """AG-UI compatible streaming endpoint for the co-pilot agent."""
    return agent.stream(request.messages, config=request.config)
```

---

## 7. Frontend Implementation

### 7.1 New Dependencies

```json
{
  "@copilotkit/react-core": "^1.x",
  "@copilotkit/react-ui": "^1.x",
  "@copilotkit/runtime": "^1.x"
}
```

### 7.2 Provider Setup

```tsx
// frontend/src/app/dashboard/layout.tsx (modified)
import { CopilotKit } from "@copilotkit/react-core";
import { CopilotPopup } from "@copilotkit/react-ui";
import "@copilotkit/react-ui/styles.css";

export default function DashboardLayout({ children }) {
  return (
    <CopilotKit runtimeUrl="/api/copilotkit">
      <DashboardShell>
        {children}
      </DashboardShell>
      <CopilotPopup
        instructions="You are the Social Media Co-Pilot assistant."
        labels={{
          title: "Co-Pilot",
          initial: "Hey! I'm your Social Media Co-Pilot. Ask me anything about your accounts, content performance, or let me help you plan your next post.",
          placeholder: "Ask about your content, metrics, or get ideas...",
        }}
        // Custom theme to match dashboard
        className="copilot-popup-custom"
      />
    </CopilotKit>
  );
}
```

### 7.3 Custom Theme Override

```css
/* frontend/src/styles/copilot-theme.css */
.copilot-popup-custom {
  --copilot-primary: #A4AC86;        /* sage */
  --copilot-background: #414833;      /* ebony */
  --copilot-text: #EBE3D2;            /* bone */
  --copilot-border: #CCBFA3;          /* dun */
  --copilot-user-bubble: #737A5D;     /* reseda */
  --copilot-assistant-bubble: #414833; /* ebony */
}
```

### 7.4 Contextual Suggestions via CopilotKit Hooks

```tsx
// frontend/src/app/dashboard/posts/[id]/page.tsx (enhanced)
import { useCopilotAction, useCopilotReadable } from "@copilotkit/react-core";

function PostDetailPage({ post }) {
  // Share current post context with the co-pilot
  useCopilotReadable({
    description: "The post currently being viewed",
    value: post,
  });

  // Register a frontend action the agent can trigger
  useCopilotAction({
    name: "scrollToMetrics",
    description: "Scroll the page to the metrics section",
    handler: async () => {
      document.getElementById("metrics-section")?.scrollIntoView({ behavior: "smooth" });
    },
  });

  // ... existing page content
}
```

---

## 8. Docker Changes

### 8.1 Backend Dockerfile Updates

Add to `backend/requirements.txt`:
```
deepagents>=0.1
langchain-openai>=0.3
ag-ui-protocol>=0.1
```

### 8.2 Docker Compose Updates

No new services required. The agent runs within the existing backend container. Redis is already available for state/session management.

---

## 9. Implementation Phases

### Phase 1 — Foundation (Core Agent + Chat UI)
**Goal**: Working floating chat connected to a Deep Agent that can query existing data.

- Set up `deepagents` in backend with Moonshot LLM
- Implement data query tools (accounts, posts, metrics, baselines)
- Create CopilotKit runtime API route in Next.js
- Add `CopilotPopup` to dashboard layout with custom theme
- Verify end-to-end: user types question → agent queries API → streams response
- Add `Artifact` and `AgentConversation` models

### Phase 2 — Intelligence (Analysis + Content Generation)
**Goal**: Agent can analyze data, spot trends, and generate content.

- Implement analysis tools (trends, comparisons, patterns, top content)
- Implement content generation tools (ideas, copy drafts, strategies)
- Add artifact save/retrieve/list tools
- Implement `useCopilotReadable` on key pages for contextual awareness
- Add suggested prompts per dashboard page

### Phase 3 — Memory (Persistent Learning)
**Goal**: Agent remembers the creator and improves over time.

- Configure LangGraph Memory Store with Redis/PostgreSQL backend
- Implement creator profile memory (niche, voice, goals, preferences)
- Implement historical knowledge memory (patterns, rejected suggestions)
- Add memory retrieval at conversation start
- Add memory update after meaningful interactions
- Implement confidence decay for stale memories

### Phase 4 — Proactive Intelligence
**Goal**: Agent surfaces insights without being asked.

- Implement proactive notifications (engagement drops, viral posts, trend opportunities)
- Add scheduled agent analysis jobs (weekly trend scan, performance anomaly detection)
- Surface proactive insights as toast notifications that open the chat
- Implement task tracking — agent creates actionable tasks, creator marks them done
- Add subagent delegation for complex multi-step analyses

---

## 10. Success Metrics

| Metric | Target |
|--------|--------|
| Chat adoption | Creator uses co-pilot ≥ 3x/week within first month |
| Query accuracy | Agent returns correct, relevant data ≥ 95% of the time |
| Content idea acceptance | ≥ 40% of generated content ideas are accepted/used |
| Memory relevance | Agent references relevant past context in ≥ 70% of sessions after month 1 |
| Time saved | Creator reports ≥ 2 hours/week saved on content planning |
| Engagement growth | Measurable improvement in baseline metrics after 3 months of co-pilot use |

---

## 11. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Moonshot API rate limits / latency | Slow agent responses | Implement response caching for repeated queries; consider model fallback |
| `moonshot-v1-8k` context window too small for complex analysis | Truncated context, poor quality | Use Deep Agent filesystem for context offloading; summarize large datasets before analysis |
| CopilotKit version incompatibility with Next.js 15 | Frontend integration issues | Pin versions; test in isolated branch before merging |
| Deep Agents library stability (new library) | Breaking changes | Pin version; wrap in abstraction layer; have LangGraph fallback plan |
| Memory grows unbounded | Performance degradation | Implement confidence decay, memory pruning (archive low-confidence entries >90 days), max entry limits |
| Agent hallucinates metrics | Creator makes bad decisions | Always ground responses in actual API data; add verification step for numeric claims |

---

## 12. Out of Scope (v1)

- Multi-user support / separate agent instances per user
- Voice input/output
- Direct posting to Instagram/TikTok from the agent
- Real-time social media monitoring (webhook-based)
- Competitor account scraping (legal/ethical concerns)
- Agent-to-agent communication (A2A protocol)
- Mobile app / React Native client

---

## 13. Dependencies & Prerequisites

- [ ] `deepagents` Python package available and compatible with Python 3.12
- [ ] CopilotKit React packages compatible with Next.js 15 App Router
- [ ] AG-UI Python SDK available for FastAPI integration
- [ ] Moonshot API key active with sufficient quota
- [ ] Existing API endpoints stable and documented (already done via CLAUDE.md)

---

## 14. References

- [LangChain Deep Agents Documentation](https://docs.langchain.com/oss/python/deepagents/overview)
- [AG-UI Protocol Documentation](https://docs.ag-ui.com/)
- [CopilotKit GitHub](https://github.com/CopilotKit/CopilotKit)
- [CopilotKit + LangChain Deep Agents Blog](https://www.copilotkit.ai/blog/how-to-build-a-frontend-for-langchain-deep-agents-with-copilotkit)
- [CopilotKit + LangGraph Integration Guide](https://www.copilotkit.ai/blog/how-to-add-a-frontend-to-any-langgraph-agent-using-ag-ui-protocol)
- [CopilotKit Next.js Integration](https://deepwiki.com/CopilotKit/CopilotKit/6.1-next.js-integration-examples)
