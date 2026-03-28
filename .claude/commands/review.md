Review recent changes for correctness, consistency, and completeness.

Steps:

1. **Check what changed**: `git diff --stat` and `git diff`

2. **Backend review checklist**:
   - [ ] New routes have `Depends(verify_password)` for auth
   - [ ] New routes have `Depends(get_db)` if they access the database
   - [ ] Pydantic schemas match the SQLAlchemy models
   - [ ] Error handling: 404 for not found, proper error messages
   - [ ] No secrets or credentials hardcoded
   - [ ] New imports are in requirements.txt if external
   - [ ] Async functions use `await` correctly

3. **Frontend review checklist**:
   - [ ] New API methods added to `lib/api.ts`
   - [ ] SWR hooks added to `lib/hooks.ts` for GET endpoints
   - [ ] Loading and error states handled
   - [ ] Color palette used correctly (bone, dun, sage, reseda, ebony)
   - [ ] No hardcoded API URLs (use the api client)
   - [ ] `'use client'` directive on interactive pages

4. **Integration review**:
   - [ ] Frontend API methods match backend endpoint paths exactly
   - [ ] Request/response shapes match between frontend and backend
   - [ ] New pages linked in sidebar navigation

5. **Documentation**:
   - [ ] CLAUDE.md updated if architecture changed
   - [ ] New env vars added to `.env.example`

Report findings as a checklist with pass/fail for each item. Flag any issues.
