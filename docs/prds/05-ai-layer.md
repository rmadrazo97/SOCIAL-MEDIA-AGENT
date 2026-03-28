# PRD-05: AI Intelligence Layer

## Domain
Post diagnostics, daily briefs, recommendations, remix generation — all powered by LLM.

## Dependencies
- PRD-01 (database)
- PRD-04 (metrics, baselines, trends)

## Goal
Turn raw analytics into clear, actionable insights. The AI layer is the core differentiator — it explains *why* a post performed the way it did and tells the creator *what to do next*.

---

## 1. AI Services Overview

| Service | Input | Output | Trigger |
|---------|-------|--------|---------|
| Post Diagnostics | Post + metrics + baseline | Why this post performed this way | On metric snapshot (24h) |
| Daily Brief | Account metrics + trends + recent posts | Daily summary + action items | Daily cron (morning) |
| Recommendations | Trends + baselines + post history | Actionable next steps | After daily brief |
| Remix Generator | Original post + performance data | Content variations | User-triggered |

## 2. API Endpoints

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/api/posts/{id}/diagnostic` | Get AI diagnostic for a post | Token |
| POST | `/api/posts/{id}/diagnostic` | Generate/regenerate diagnostic | Token |
| GET | `/api/accounts/{id}/brief` | Get today's daily brief | Token |
| GET | `/api/accounts/{id}/briefs` | List past briefs | Token |
| GET | `/api/accounts/{id}/recommendations` | Get active recommendations | Token |
| PATCH | `/api/recommendations/{id}` | Update status (accept/dismiss) | Token |
| POST | `/api/posts/{id}/remix` | Generate content variations | Token |

## 3. Post Diagnostics

### What It Does
Analyzes a single post's performance relative to the creator's baseline and explains why it performed the way it did.

### Input Context (sent to LLM)
```json
{
  "post": {
    "caption": "...",
    "post_type": "reel",
    "posted_at": "2026-03-27T14:00:00Z"
  },
  "metrics": {
    "views": 25000,
    "likes": 2100,
    "comments": 85,
    "shares": 120,
    "saves": 340,
    "engagement_rate": 0.106
  },
  "baseline": {
    "avg_views": 12000,
    "avg_engagement_rate": 0.065,
    "avg_shares": 45
  },
  "performance_score": 82,
  "account_context": {
    "platform": "instagram",
    "follower_count": 25000,
    "niche_hint": "fitness"
  }
}
```

### Output Schema
```json
{
  "summary": "This reel performed 2x above your average. Strong share-to-view ratio suggests high relatability.",
  "performance_label": "above_average",  // "viral", "above_average", "average", "below_average", "underperforming"
  "key_factors": [
    {
      "factor": "Timing",
      "impact": "positive",
      "explanation": "Posted at 2PM on Thursday — your best performing window."
    },
    {
      "factor": "Caption hook",
      "impact": "positive",
      "explanation": "Opening question drove comments. Direct CTA increased saves."
    },
    {
      "factor": "Share ratio",
      "impact": "positive",
      "explanation": "120 shares (2.7x your avg) — content is highly shareable/relatable."
    }
  ],
  "what_to_repeat": ["Question-based hooks", "Thursday afternoon posting"],
  "what_to_improve": ["Add more carousel slides for higher saves"]
}
```

### LLM Prompt Strategy
- System prompt: "You are a social media analytics expert..."
- Include baseline context so the LLM understands relative performance
- Request structured JSON output
- Temperature: 0.3 (consistent analysis)

## 4. Daily Brief

### What It Does
A morning summary of the creator's account performance, highlighting what happened yesterday, what's trending, and what to focus on today.

### Input Context
```json
{
  "account": { "platform": "instagram", "username": "...", "followers": 25000 },
  "yesterday": {
    "new_posts": 1,
    "total_views": 32000,
    "total_engagement": 2800,
    "top_post": { "caption": "...", "views": 25000, "score": 82 }
  },
  "week_trend": {
    "direction": "growing",
    "growth_rate": 0.12,
    "avg_daily_views": 28000,
    "vs_last_week": "+15%"
  },
  "active_posts": [
    { "caption": "...", "posted_hours_ago": 6, "current_views": 8000, "velocity": "fast" }
  ],
  "baseline": { ... }
}
```

### Output Schema
```json
{
  "greeting": "Good morning! Here's your Instagram recap for March 28.",
  "headline": "Strong day — your reel hit 2x your average views.",
  "sections": [
    {
      "title": "Yesterday's Performance",
      "content": "You posted 1 reel that reached 25K views (2x your baseline). Engagement rate was 10.6%, well above your 6.5% average."
    },
    {
      "title": "Weekly Trend",
      "content": "You're up 15% vs last week. Consistent posting and strong share rates are driving growth."
    },
    {
      "title": "Active Posts",
      "content": "Your latest post (6h ago) is gaining traction fast — 8K views already. On pace to outperform your average."
    }
  ],
  "action_items": [
    "Post another reel today — momentum is in your favor",
    "Reply to comments on yesterday's viral post to boost engagement",
    "Try a carousel post this week — you haven't posted one in 10 days"
  ],
  "metrics_snapshot": {
    "followers": 25000,
    "weekly_views": 196000,
    "weekly_engagement_rate": 0.078
  }
}
```

### Generation Schedule
- Run daily at 8:00 AM user's local timezone (default UTC if unknown)
- Store in `daily_briefs` table
- Keep last 30 days of briefs

## 5. Recommendations Engine

### What It Does
Generates actionable recommendations based on trends, baseline data, and recent performance.

### Recommendation Types

| Type | Example |
|------|---------|
| `content_idea` | "Post a behind-the-scenes reel — your audience engages 40% more with authentic content" |
| `timing` | "Your best window is Thursday 2-4PM. Schedule your next post there." |
| `hashtag` | "Try #fitnessmotivation — posts with niche hashtags get 25% more reach for your account size" |
| `format` | "Switch to carousel — your carousels get 30% more saves than single images" |
| `engagement` | "Reply to comments within 1 hour — it boosts your post in the algorithm" |
| `remix` | "Your top post this week could be remixed as a carousel breakdown" |

### Generation Logic
1. After daily brief is generated
2. Analyze trends, baseline, recent post performance
3. Generate 3-5 recommendations
4. Deduplicate against recent recommendations (last 7 days)
5. Prioritize by potential impact (1-5)

### Output Schema
```json
{
  "recommendations": [
    {
      "type": "content_idea",
      "title": "Post a Q&A reel",
      "content": "Your question-based hooks drive 2x more comments. Film a quick Q&A reel answering your most common DM question.",
      "priority": 5,
      "reasoning": "Based on your top 3 posts this month, all using question hooks."
    }
  ]
}
```

## 6. Remix Generator

### What It Does
Takes an existing post and generates content variations the creator can use.

### Input
```json
{
  "original_post": {
    "caption": "5 morning habits that changed my life...",
    "post_type": "reel",
    "performance_score": 85
  },
  "remix_type": "carousel"  // or "reel_script", "thread", "story_series"
}
```

### Output
```json
{
  "remixes": [
    {
      "format": "carousel",
      "title": "5 Morning Habits That Changed My Life",
      "slides": [
        { "slide": 1, "text": "Hook: The routine that 10x'd my productivity", "visual_note": "Bold text on gradient" },
        { "slide": 2, "text": "1. Wake up at 5:30 AM...", "visual_note": "Split image" }
      ],
      "caption": "Save this for tomorrow morning...",
      "hashtags": ["#morningroutine", "#productivity"]
    },
    {
      "format": "reel_script",
      "hook": "POV: You finally fix your morning routine",
      "script": "...",
      "caption": "...",
      "audio_suggestion": "trending audio: 'that girl' trend"
    }
  ]
}
```

## 7. LLM Configuration

### Provider
- **OpenAI API** (GPT-4o or GPT-4o-mini depending on task)
- Use GPT-4o for diagnostics and briefs (quality matters)
- Use GPT-4o-mini for remixes and recommendations (speed + cost)

### Service Architecture
```python
class AIService:
    async def generate_diagnostic(self, post_context: dict) -> PostDiagnostic: ...
    async def generate_daily_brief(self, account_context: dict) -> DailyBrief: ...
    async def generate_recommendations(self, account_context: dict) -> list[Recommendation]: ...
    async def generate_remix(self, post_context: dict, remix_type: str) -> list[Remix]: ...

    # Internal
    async def _call_llm(self, messages: list, model: str, temperature: float) -> dict: ...
```

### Prompt Management
- Store prompts as templates in `app/prompts/` directory
- Use Jinja2 or f-strings for variable injection
- Version prompts (comment with version number)

### Error Handling
- Retry on API timeout (max 2 retries)
- Fallback to simpler model if primary fails
- Log all LLM calls for debugging (input hash + output, not full content)
- Budget tracking: log token usage per call

## 8. Acceptance Criteria

- [ ] Post diagnostic generated for any post with 24h+ of metrics
- [ ] Diagnostic explains performance relative to baseline
- [ ] Daily brief generated every morning per account
- [ ] Brief includes yesterday's metrics, weekly trend, and action items
- [ ] 3-5 recommendations generated daily per account
- [ ] Recommendations are deduplicated (no repeats within 7 days)
- [ ] Remix generator produces 2-3 variations per request
- [ ] All AI outputs stored in database
- [ ] LLM errors handled gracefully (no user-facing crashes)
- [ ] Token usage tracked per request

## 9. Out of Scope (MVP)
- Fine-tuned models
- User feedback loop on AI quality
- A/B testing of prompts
- Multi-language support
- Voice/audio content analysis
