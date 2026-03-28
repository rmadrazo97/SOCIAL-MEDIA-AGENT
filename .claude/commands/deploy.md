Build, restart, and verify the full stack. Use this after making changes.

Run these steps in order:

1. **Check what changed** — `git diff --name-only` to determine which services need rebuilding

2. **Rebuild affected services**:
   - If backend files changed: `docker compose up --build -d backend`
   - If frontend files changed: `docker compose up --build -d frontend`
   - If docker-compose.yml or .env changed: `docker compose up --build -d`
   - If only Python files in backend/ changed (not Dockerfile or requirements.txt), hot reload handles it — just wait 3 seconds

3. **Verify startup**:
   - `docker compose ps` — all containers should be "running" or "healthy"
   - `curl -s http://localhost:8001/health` — should return `{"status": "ok"}`
   - Check for errors: `docker compose logs backend --tail 20 --since 30s`
   - Check frontend: `docker compose logs frontend --tail 10 --since 30s`

4. **Verify data** (if applicable):
   - `curl -s http://localhost:8001/api/accounts -H "X-App-Password: admin123"` — should return accounts

5. **Report** — Summarize: which services were rebuilt, if startup was clean, any errors found.

If there are errors:
- Python import errors → check requirements.txt, rebuild backend
- TypeScript errors → check frontend logs, may need `docker compose exec frontend npm install`
- DB connection errors → check if db container is healthy: `docker compose ps db`
