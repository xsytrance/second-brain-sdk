# Troubleshooting

Common errors and how to resolve them.

---

## FOREIGN KEY constraint failed (SQLite)

**Error**: `sqlite3.IntegrityError: FOREIGN KEY constraint failed`

**Cause**: You attempted to log an event with a `session_id` that doesn't exist in the `sessions` table.

**Solution**:
- Ensure you create a session before logging events with that session_id:
  ```python
  sid = brain.start_session(agent_id="my-agent", project="demo")
  brain.log_event(..., session_id=sid)
  ```
- If using raw SQL/other frameworks, insert a session row first.
- Starting from SDK v0.2.0, the FK constraint is DEFERRABLE, so you can insert both in one transaction in any order — but you still need both rows present before commit.

**Historical note**: Pre-v0.2.0 the FK was immediate; you had to create the session before any events referencing it in separate transactions. This is no longer the case, but existing databases may need a schema update. Run:
```bash
# Re-initialize to get new schema (WARNING: deletes all data)
rm ~/.second-brain/brain.db
second-brain init
```
Or manually apply the ALTER TABLE migration (see repo issues).

---

## Missing foreign key table / no such table: sessions

**Cause**: You're using a newer SDK feature (sessions) against an old database created before sessions table existed.

**Solution**: Re-initialize (loses data) or migrate manually:
```sql
-- Connect to brain.db
sqlite3 ~/.second-brain/brain.db

-- Create sessions table (copy from schema.sql)
CREATE TABLE IF NOT EXISTS sessions (
  id TEXT PRIMARY KEY,
  started_at TEXT NOT NULL,
  ended_at TEXT,
  agent_id TEXT,
  project TEXT
);
-- Also add FK to events if missing (requires table rebuild)
```

Simpler: delete `brain.db` and run `second-brain init` again.

---

## Key loss / corrupted encryption

**Symptom**: `cryptography.fernet.InvalidToken` when calling `get_credential`.

**Cause**: `brain.key` is missing, corrupted, or changed.

**Solution**:
- Restore `brain.key` from backup to `~/.second-brain/brain.key`.
- If lost, encrypted credentials are unrecoverable. You must re-enter them.
- Export credentials before deleting the key: `second-brain credential list` (shows metadata, not values).

**Prevention**: Back up `brain.key` to a password manager or remote host:
```bash
scp ~/.second-brain/brain.key backup-host:~/backups/
```

---

## Token auth failed (server mode)

**Symptom**: 401/403 from `/v1/events`.

**Causes & fixes**:
- Token not provided: ensure `Authorization: Bearer <token>` header.
- Wrong token: verify token with `second-brain server token-list` and compare.
- Token revoked: check `revoked_at` column in DB; create a new token.
- Wrong scope: token must include `events:write`. Recreate with `token-create`.

---

## Brain directory not writable

**Error**: `PermissionError: [Errno 13] Permission denied` when writing to `~/.second-brain`.

**Fix**:
```bash
chmod u+rwx ~/.second-brain
# Or change location:
export SECOND_BRAIN_DIR=/tmp/my-brain
```

---

## Import errors / module not found

**Cause**: Second Brain not installed in the active Python environment.

**Fix**:
```bash
# Check which Python you're running
which python
# Activate correct venv if using one
source ~/.hermes/hermes-agent/venv/bin/activate
pip install second-brain
```

---

## Schema version mismatch

**Error**: Database schema is older than expected.

Second Brain stores `schema_version` in `meta` table. If you cloned an old brain.db, you may need to manually upgrade or re-init.

**Fix**: Re-init with fresh schema (data loss) or apply migration manually from `docs/SCHEMA_MIGRATIONS.md`.

---

## Still stuck?

Open an issue on GitHub: https://github.com/xsytrance/second-brain-sdk/issues  
Include:
- Second Brain version (`pip show second-brain`)
- OS and Python version
- Full error traceback
- `second-brain status` output (future command)

