# Second Brain — Standalone Generalization Checklist (SQLite + optional server)

## Scope (locked)
- Storage: **SQLite**
- Encryption at rest: **credentials only** (event details plaintext for search)
- Server extra: **write-only** agent tokens (no agent read endpoints in v1)

---

## Phase 0 — Repo hygiene + packaging identity

### 0.1 Create a working branch
- [x] `git checkout -b generalize-standalone`

### 0.2 Rename for public packaging
- [ ] PyPI name: `second-brain`
- [ ] Import package: `second_brain`
- [ ] CLI entrypoint: `second-brain`

### 0.3 Restructure package layout
- [ ] Move `second_brain_sdk/` → `second_brain/`
- [ ] Keep public imports in `second_brain/__init__.py`

### 0.4 Dependencies
- [ ] Keep: `cryptography`
- [ ] Add: `pydantic`, `typer`
- [ ] Optional extra `[server]`: `fastapi`, `uvicorn`

### 0.5 Remove/ignore build artifacts
- [ ] Add to `.gitignore`: `dist/`, `dist_wheel/`, `*.whl`, `*.tar.gz`

---

## Phase 1 — SQLite core

### 1.1 Schema (SQLite)
- [ ] Create DDL + migrations
- Tables:
  - [ ] `events`
  - [ ] `credentials` (stores encrypted values)
  - [ ] `sessions`
  - [ ] `meta` (schema version)

### 1.2 Storage layer
- [ ] `SQLiteStore` with:
  - [ ] WAL mode
  - [ ] transactions
  - [ ] basic CRUD for events/credentials/sessions

### 1.3 Key management
- [ ] Default brain dir: `~/.second-brain/` or env `SECOND_BRAIN_DIR`
- [ ] Key file: `brain.key`
- [ ] Credentials encrypted with Fernet

### 1.4 Public API
- [ ] `Brain` object
- [ ] `Session` context manager
- [ ] `Query` builder
- [ ] `Credentials` manager

### 1.5 Compatibility
- [ ] (Optional) one-way importer for legacy encrypted JSON vault

---

## Phase 2 — CLI

- [ ] `second-brain init`
- [ ] `second-brain log TYPE TITLE [--details --project --outcome --tag --agent --session]`
- [ ] `second-brain events [--project --agent --failed --limit]`
- [ ] `second-brain credential add/list/get`
- [ ] `second-brain info`

---

## Phase 3 — Optional server extra (write-only)

### 3.1 FastAPI app
- [ ] `POST /v1/events` (requires agent token)
- [ ] Token auth:
  - [ ] store `token_hash` (never raw token)
  - [ ] scopes: `events:write`

### 3.2 Admin token management (local only)
- [ ] CLI: `second-brain token create/list/revoke`

---

## Phase 4 — Tests + docs

- [ ] Unit tests:
  - [ ] credential encryption roundtrip
  - [ ] event logging + query
  - [ ] sqlite migration
- [ ] Docs:
  - [ ] README Quickstart (local)
  - [ ] Server quickstart (optional)
- [ ] Examples:
  - [ ] `examples/basic_agent.py`

---

## Release readiness
- [ ] `python -m build`
- [ ] `twine check dist/*`
- [ ] Install wheel in clean venv and run quickstart
