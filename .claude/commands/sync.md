Trigger data synchronization and report results.

Run these steps:

1. **Sync all accounts**:
   ```bash
   curl -s -X POST http://localhost:8001/api/sync/all -H "X-App-Password: admin123"
   ```

2. **Wait for sync to complete** — watch logs for 30-60 seconds:
   ```bash
   sleep 30 && docker compose logs backend --tail 30 --since 1m 2>&1 | grep -iE "(sync|scrape|error|warning|complete)"
   ```

3. **Recompute baselines**:
   ```bash
   curl -s -X POST http://localhost:8001/api/sync/baselines -H "X-App-Password: admin123"
   ```

4. **Check results**:
   ```bash
   docker compose exec -T db psql -U smadmin -d social_media_agent -c "
   SELECT a.username, a.platform, a.follower_count,
          (SELECT count(*) FROM posts p WHERE p.account_id = a.id) as posts,
          (SELECT count(*) FROM post_metrics pm JOIN posts p2 ON p2.id = pm.post_id WHERE p2.account_id = a.id) as metrics
   FROM accounts a;"
   ```

5. **Report** — Summarize: which accounts synced, how many new posts, any errors.

If scraping failed:
- Instagram "challenge required" → user needs to approve login from Instagram app
- TikTok "could not extract state data" → datacenter IP blocked, need TIKTOK_PROXY
- Timeout errors → increase timeout or check network connectivity
