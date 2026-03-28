Inspect the database to understand current state. Optionally pass a table name to inspect.

Run these queries:

1. **Table list and row counts**:
   ```bash
   docker compose exec -T db psql -U smadmin -d social_media_agent -c "
   SELECT 'accounts' as table_name, count(*) FROM accounts UNION ALL
   SELECT 'posts', count(*) FROM posts UNION ALL
   SELECT 'post_metrics', count(*) FROM post_metrics UNION ALL
   SELECT 'insights', count(*) FROM insights UNION ALL
   SELECT 'recommendations', count(*) FROM recommendations UNION ALL
   SELECT 'daily_briefs', count(*) FROM daily_briefs UNION ALL
   SELECT 'account_baselines', count(*) FROM account_baselines
   ORDER BY 1;"
   ```

2. **Account summary**:
   ```bash
   docker compose exec -T db psql -U smadmin -d social_media_agent -c "
   SELECT a.username, a.platform, a.follower_count, a.status,
          (SELECT count(*) FROM posts p WHERE p.account_id = a.id) as posts,
          (SELECT max(pm.snapshot_at) FROM post_metrics pm JOIN posts p2 ON p2.id = pm.post_id WHERE p2.account_id = a.id) as last_metric
   FROM accounts a
   ORDER BY a.created_at;"
   ```

3. **If a specific table is requested**, describe it and show sample rows:
   ```bash
   docker compose exec -T db psql -U smadmin -d social_media_agent -c "\d <table>"
   docker compose exec -T db psql -U smadmin -d social_media_agent -c "SELECT * FROM <table> ORDER BY created_at DESC LIMIT 5;"
   ```

4. **Recent activity**:
   ```bash
   docker compose exec -T db psql -U smadmin -d social_media_agent -c "
   SELECT 'latest post' as item, posted_at::text as ts FROM posts ORDER BY posted_at DESC LIMIT 1
   UNION ALL
   SELECT 'latest metric', snapshot_at::text FROM post_metrics ORDER BY snapshot_at DESC LIMIT 1
   UNION ALL
   SELECT 'latest brief', created_at::text FROM daily_briefs ORDER BY created_at DESC LIMIT 1;"
   ```

Report the results in a clear summary.

$ARGUMENTS
