Add support for a new social media platform. The user will specify which platform.

Follow this workflow:

1. **Scraper** — Create `backend/app/integrations/<platform>_scraper.py`
   - Implement a class with these methods:
     - `async def get_profile(self, username: str) -> dict | None`
       Returns: `{username, full_name, biography, follower_count, following_count, post_count, profile_pic_url, is_private, platform_user_id}`
     - `async def get_recent_posts(self, username: str, limit: int = 20) -> list[dict]`
       Each post: `{platform_post_id, platform, post_type, caption, media_url, permalink, posted_at (ISO), metrics: {views, likes, comments, shares, saves, reach}}`
   - Export a singleton: `<platform>_scraper = <Platform>Scraper()`
   - Handle errors gracefully (return None/empty list)

2. **Config** — Add any needed env vars to `backend/app/config.py` in the Settings class

3. **Sync routing** — Update `backend/app/services/sync_service.py`:
   - Import the new scraper
   - Add `elif account.platform == "<platform>":` branches in `_scrape_profile()` and `_scrape_posts()`

4. **Frontend** — Update the account creation form in `frontend/src/app/dashboard/accounts/page.tsx`:
   - Add the platform to the platform selector dropdown
   - Add a platform icon/color

5. **Environment** — Add any new env vars to `.env.example` and document in `CLAUDE.md`

6. **Test** — Add an account and trigger sync:
   ```bash
   curl -X POST http://localhost:8001/api/accounts \
     -H "X-App-Password: admin123" -H "Content-Type: application/json" \
     -d '{"platform": "<platform>", "username": "<test_username>"}'
   ```

$ARGUMENTS
