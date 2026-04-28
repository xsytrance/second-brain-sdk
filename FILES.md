# Second Brain — File Index

## 🗂️ Repository Structure

```
second-brain/
├── README.md                    # Main project documentation
├── LICENSE                      # MIT License
├── pyproject.toml               # Build configuration
├── requirements.txt             # Runtime dependencies (convenience)
├── .gitignore                   # Git ignore rules
├── second_brain/
│   ├── __init__.py              # Public exports
│   ├── cli.py                   # Typer-based CLI entrypoint
│   ├── brain.py                 # SQLite Brain core (events + encrypted credentials)
│   ├── crypto/
│   │   └── keys.py              # Fernet key management
│   ├── models/
│   │   └── credential.py        # Pydantic record(s)
│   ├── storage/
│   │   ├── schema.sql           # SQLite schema (events, credentials, tokens)
│   │   └── sqlite_store.py      # SQLiteStore (WAL mode, transactions)
│   └── server/
│       ├── __init__.py          # Optional server entry
│       └── app.py               # FastAPI write-only ingestion
├── examples/
│   ├── quickstart.py            # Minimal example using Brain
│   ├── agent_workflow.py        # Example workflow (events + credentials)
│   └── hermes_integration.py    # Framework-agnostic integration pattern
├── tests/
│   └── test_sdk.py              # Legacy Vault tests (kept while migrating)
└── docs/
    ├── USAGE.md                 # Standalone usage guide
    └── PLAN_CHECKLIST.md        # Generalization plan/checklist
```

---

## Storage files on disk (runtime)

Default brain directory: `~/.second-brain/` (override with `SECOND_BRAIN_DIR`)

- `brain.db` — SQLite database
  - `events` table stores plaintext event logs
  - `credentials` table stores encrypted credential values (`value_enc`)
  - `api_tokens` table stores hashed write tokens for server mode

- `brain.key` — Fernet key for credential encryption/decryption

**Back up `brain.key`.** Without it, encrypted credentials cannot be recovered.

---

## Optional server mode

Install extras:
```bash
pip install 'second-brain[server]'
```

Run:
```bash
second-brain init
second-brain server token-create --agent agentA
second-brain server serve --host 0.0.0.0 --port 8009
```

Write events:
```bash
curl -X POST http://localhost:8009/v1/events \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"type":"task_started","title":"hello"}'
```
