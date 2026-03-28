Debug an issue in the Social Media Agent. The user will describe the problem.

Debugging workflow:

1. **Gather context**:
   - `docker compose ps` — check service health
   - `docker compose logs backend --tail 50 --since 5m` — recent backend errors
   - `docker compose logs frontend --tail 30 --since 5m` — recent frontend errors
   - `curl -s http://localhost:8001/health` — backend reachable?

2. **Identify the layer**:
   - **Frontend error** → Check browser console, inspect `frontend/src/` code
   - **API error (4xx/5xx)** → Check the route in `backend/app/api/`, look at logs
   - **Scraping failure** → Check `backend/app/integrations/`, look for rate limits or auth issues
   - **AI failure** → Check `backend/app/services/ai_service.py`, verify MOONSHOT_API_KEY
   - **Database error** → Check model definitions, run `docker compose exec db psql -U smadmin -d social_media_agent`
   - **Scheduler issue** → Check `backend/app/workers/scheduler.py`, look for job execution logs

3. **Check data**:
   ```bash
   docker compose exec -T db psql -U smadmin -d social_media_agent -c "
   SELECT 'accounts' as t, count(*) FROM accounts UNION ALL
   SELECT 'posts', count(*) FROM posts UNION ALL
   SELECT 'post_metrics', count(*) FROM post_metrics
   ORDER BY 1;"
   ```

4. **Test in isolation**:
   - Backend: `docker compose exec backend python -c "from app.integrations.tiktok_scraper import tiktok_scraper; ..."`
   - API: `curl -s http://localhost:8001/api/<path> -H "X-App-Password: admin123" | python3 -m json.tool`
   - Database: `docker compose exec -T db psql -U smadmin -d social_media_agent -c "<query>"`

5. **Fix and verify** — After fixing, run `/deploy` to rebuild and verify.

$ARGUMENTS
