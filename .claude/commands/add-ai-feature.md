Add a new AI-powered feature. The user will describe what the feature should do.

Follow this workflow:

1. **AI method** — Add a method to `backend/app/services/ai_service.py`
   - Define a clear `system_prompt` telling the LLM its role and exact JSON structure to return
   - Build a `user_prompt` with relevant data (post content, metrics, baseline, etc.)
   - Call `self._call_llm(system_prompt, user_prompt)` — it returns a dict
   - The method auto-falls back to `_mock_response()` if the API key is missing
   - Use `model="moonshot-v1-8k"` (default) for most features

2. **API endpoint** — Expose via FastAPI:
   - Schema in `schemas/schemas.py` for the response
   - Route in the appropriate `api/*.py` file
   - Fetch needed data (post, metrics, baseline) inside the route
   - Call the AI service method
   - Store results if persistent (Insight, Recommendation, etc.)

3. **Frontend** — Wire up:
   - Add API method in `lib/api.ts`
   - Add button/section in the appropriate page
   - Show loading state while generating
   - Render the AI response (markdown for text, structured for lists)

AI service patterns:
- All prompts end with "You MUST respond with valid JSON only."
- Temperature: 0.3 (factual/consistent)
- JSON response is auto-parsed; code blocks are stripped
- Mock responses are returned when API is unavailable
- Existing features: diagnostic, daily_brief, recommendations, remix

Example system prompt structure:
```python
system_prompt = """You are a [role]. [Task description].
Return JSON with these exact keys: [key1] ([type]), [key2] ([type]), ..."""
```

$ARGUMENTS
