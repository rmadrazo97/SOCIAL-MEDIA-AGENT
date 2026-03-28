Check the health and status of all services in the Social Media Agent stack.

Run:
1. `docker compose ps` to show container status
2. `curl http://localhost:8001/health` to check backend health
3. `curl http://localhost:3001` to check frontend
4. `docker compose logs backend --tail 10` for recent backend activity
5. Query the database for row counts:
   ```
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

Report the results clearly: which services are up/down, recent errors, and data counts.
