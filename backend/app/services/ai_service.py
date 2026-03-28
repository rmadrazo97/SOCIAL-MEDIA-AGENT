import json
import logging
from app.config import settings

logger = logging.getLogger(__name__)

try:
    from openai import AsyncOpenAI
    openai_available = True
except ImportError:
    openai_available = False


class AIService:
    def __init__(self):
        self.client = None
        if openai_available and settings.MOONSHOT_API_KEY:
            self.client = AsyncOpenAI(
                api_key=settings.MOONSHOT_API_KEY,
                base_url="https://api.moonshot.cn/v1",
            )

    async def _call_llm(self, system_prompt: str, user_prompt: str, model: str = "moonshot-v1-8k") -> dict:
        if not self.client:
            return self._mock_response(user_prompt)

        try:
            response = await self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt + "\n\nYou MUST respond with valid JSON only."},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
            )
            text = response.choices[0].message.content.strip()
            # Try to extract JSON from response
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            return json.loads(text)
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return self._mock_response(user_prompt)

    def _mock_response(self, context: str) -> dict:
        return {
            "summary": "AI analysis is unavailable. Configure MOONSHOT_API_KEY to enable AI-powered insights.",
            "content": "AI analysis requires a Moonshot API key. Please set MOONSHOT_API_KEY in your .env file.",
            "key_factors": [],
            "what_to_repeat": [],
            "what_to_improve": [],
            "performance_label": "unknown",
            "action_items": ["Set up MOONSHOT_API_KEY to enable AI features"],
            "metrics_snapshot": {},
            "recommendations": [],
        }

    async def generate_diagnostic(self, post, metrics, baseline) -> dict:
        baseline_data = baseline.baseline_data if baseline else {}
        metrics_dict = {
            "views": metrics.views if metrics else 0,
            "likes": metrics.likes if metrics else 0,
            "comments": metrics.comments if metrics else 0,
            "shares": metrics.shares if metrics else 0,
            "saves": metrics.saves if metrics else 0,
            "engagement_rate": float(metrics.engagement_rate) if metrics else 0,
        }

        system_prompt = """You are a social media analytics expert. Analyze post performance relative to the creator's baseline.
Return JSON with these exact keys: summary (string), performance_label (one of: viral, above_average, average, below_average, underperforming),
key_factors (array of objects with keys: factor, impact, explanation), what_to_repeat (array of strings), what_to_improve (array of strings)."""

        user_prompt = f"""Post: {post.caption or 'No caption'}
Type: {post.post_type}, Platform: {post.platform}
Posted: {post.posted_at}
Metrics: {json.dumps(metrics_dict)}
Baseline: {json.dumps(baseline_data)}"""

        return await self._call_llm(system_prompt, user_prompt)

    async def generate_daily_brief(self, account, post_data, baseline) -> dict:
        baseline_data = baseline.baseline_data if baseline else {}

        posts_summary = []
        total_views = 0
        total_likes = 0
        for pd in post_data[:10]:
            p = pd["post"]
            m = pd["metrics"]
            views = m.views if m else 0
            likes = m.likes if m else 0
            total_views += views
            total_likes += likes
            posts_summary.append({
                "caption": (p.caption or "")[:100],
                "type": p.post_type,
                "posted": str(p.posted_at),
                "views": views,
                "likes": likes,
            })

        system_prompt = """You are a social media coach. Generate a daily performance brief.
Return JSON with these exact keys: content (string, markdown formatted brief), action_items (array of strings),
metrics_snapshot (object with key totals), headline (string, one-line summary)."""

        user_prompt = f"""Account: {account.username} ({account.platform})
Followers: {account.follower_count or 'unknown'}
Recent posts: {json.dumps(posts_summary)}
Baseline: {json.dumps(baseline_data)}
Total recent views: {total_views}, Total recent likes: {total_likes}"""

        result = await self._call_llm(system_prompt, user_prompt)
        if "content" not in result:
            result["content"] = result.get("summary", "No brief available.")
        return result

    async def generate_recommendations(self, account, post_data, baseline) -> list[dict]:
        baseline_data = baseline.baseline_data if baseline else {}

        system_prompt = """You are a social media strategist. Generate actionable recommendations.
Return JSON with one key: recommendations (array of objects, each with keys: type, title, content, priority (integer 1-5), reasoning).
Valid types: content_idea, timing, hashtag, format, engagement, remix."""

        posts_info = []
        for pd in post_data[:10]:
            p = pd["post"]
            m = pd["metrics"]
            posts_info.append({
                "caption": (p.caption or "")[:80],
                "type": p.post_type,
                "views": m.views if m else 0,
                "engagement": float(m.engagement_rate) if m else 0,
            })

        user_prompt = f"""Account: {account.username} ({account.platform})
Recent posts: {json.dumps(posts_info)}
Baseline: {json.dumps(baseline_data)}"""

        result = await self._call_llm(system_prompt, user_prompt)
        return result.get("recommendations", [])

    async def generate_remix(self, post, metrics, remix_type: str) -> list[dict]:
        metrics_dict = {}
        if metrics:
            metrics_dict = {
                "views": metrics.views, "likes": metrics.likes,
                "comments": metrics.comments, "shares": metrics.shares,
            }

        system_prompt = f"""You are a creative content strategist. Generate {remix_type} variations of this post.
Return JSON with one key: remixes (array of objects, each with keys: format, title, and content details).
For carousel: include a slides array. For reel_script: include hook, script, caption. For story_series: include frames array."""

        user_prompt = f"""Original post: {post.caption or 'No caption'}
Type: {post.post_type}, Platform: {post.platform}
Performance: {json.dumps(metrics_dict)}
Requested format: {remix_type}"""

        result = await self._call_llm(system_prompt, user_prompt)
        remixes = result.get("remixes", [])
        if not remixes:
            remixes = [{"format": remix_type, "title": "Remix unavailable", "content": "Configure MOONSHOT_API_KEY for remix generation."}]
        return remixes


ai_service = AIService()
