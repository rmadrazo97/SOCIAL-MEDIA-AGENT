Add a new database model. The user will describe the entity.

Follow this workflow:

1. **Model** — Add SQLAlchemy model to `backend/app/models/models.py`
   - Use UUID primary key: `id = Column(pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)`
   - Add `created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)`
   - Add appropriate foreign keys with `ondelete="CASCADE"`
   - Add relationships to related models
   - Add indexes on commonly queried columns
   - Add unique constraints where appropriate
   - Follow the pattern of existing models in the file

2. **Schema** — Add Pydantic schemas to `backend/app/schemas/schemas.py`
   - `<Name>Create` — for POST requests (exclude id, created_at)
   - `<Name>Out` — for responses (include all fields)
   - Use `model_config = ConfigDict(from_attributes=True)`

3. **Migration** — Tables auto-create on startup via `init_db.py`, but for existing databases you need to either:
   - Reset: `docker compose exec -T db psql -U smadmin -d social_media_agent -c "DROP TABLE IF EXISTS <table_name>;"`
   - Or add manually: `docker compose exec -T db psql -U smadmin -d social_media_agent -c "CREATE TABLE ..."`
   - Then restart: `docker compose restart backend`

4. **Verify** — Check the table was created:
   ```bash
   docker compose exec -T db psql -U smadmin -d social_media_agent -c "\d <table_name>"
   ```

5. **Update CLAUDE.md** — Add the model to the Database Models section

Conventions:
- All UUIDs, all timezone-aware timestamps
- Foreign keys cascade on delete
- JSONB for flexible/nested data
- Numeric(7,4) for rates/percentages
- Nullable fields should be explicitly marked

$ARGUMENTS
