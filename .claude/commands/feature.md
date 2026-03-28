Plan and implement a new feature end-to-end. The user will describe the feature.

Workflow:

1. **Plan** — Before writing code, outline:
   - What database changes are needed (new models, new columns)?
   - What API endpoints are needed?
   - What frontend pages/components are needed?
   - What services or integrations are needed?
   - Are there any cron/scheduler jobs?

2. **Implement in order**:
   a. **Database model** (if needed) → `backend/app/models/models.py`
   b. **Pydantic schemas** → `backend/app/schemas/schemas.py`
   c. **Service logic** → `backend/app/services/`
   d. **API routes** → `backend/app/api/`
   e. **Register router** → `backend/app/main.py` (if new file)
   f. **Frontend API client** → `frontend/src/lib/api.ts`
   g. **Frontend hook** → `frontend/src/lib/hooks.ts`
   h. **Frontend page/component** → `frontend/src/app/dashboard/`
   i. **Navigation link** → `frontend/src/components/layout/DashboardLayout.tsx`

3. **Deploy** — Run `/deploy` to rebuild and verify

4. **Test** — Verify the feature works:
   - Hit the API endpoint with curl
   - Check the frontend page loads
   - Verify data flows from backend to frontend

5. **Document** — Update CLAUDE.md if the feature adds new:
   - Models, endpoints, services, env vars, or architectural patterns

Key files to read before starting:
- `backend/app/models/models.py` — all models
- `backend/app/schemas/schemas.py` — all schemas
- `backend/app/main.py` — router registration
- `frontend/src/lib/api.ts` — API client
- `frontend/src/lib/hooks.ts` — data hooks
- `frontend/src/components/layout/DashboardLayout.tsx` — sidebar nav

$ARGUMENTS
