Add a new API endpoint to the backend. The user will describe what the endpoint should do.

Follow this exact workflow:

1. **Schema** — Add Pydantic request/response models in `backend/app/schemas/schemas.py`
2. **Route** — Add the FastAPI route in the appropriate `backend/app/api/*.py` file (or create a new one)
   - Use `Depends(verify_password)` for auth
   - Use `Depends(get_db)` for database access
   - Follow existing patterns in the file
3. **Register** — If you created a new router file, register it in `backend/app/main.py`
4. **Frontend API client** — Add the corresponding method in `frontend/src/lib/api.ts`
5. **SWR hook** — If it's a GET endpoint, add a hook in `frontend/src/lib/hooks.ts`
6. **Test** — Verify the endpoint works:
   ```bash
   curl -s http://localhost:8001/api/<path> -H "X-App-Password: admin123" | python3 -m json.tool
   ```

Conventions:
- All endpoints are under `/api/`
- List endpoints return arrays directly (no pagination wrappers)
- Background tasks return `{"status": "..._started"}` immediately
- Use 201 for creation, 204 for deletion, 404 for not found
- Error responses: `{"detail": "message"}`

$ARGUMENTS
