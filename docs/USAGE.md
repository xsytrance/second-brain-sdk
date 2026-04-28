# Second Brain  Usage Guide (Standalone)

This guide documents the **standalone** Second Brain package.

**Core facts:**
- Storage: **SQLite** (`brain.db`)
- Credentials: **encrypted at rest** with Fernet (`brain.key`)
- Events: plaintext for searchability
- Optional server extra: `second-brain[server]` (write-only ingestion)

---

## Quick Start

```python
from second_brain import Brain

brain = Brain.default()
brain.init()

brain.log_event(type="milestone", title="First event logged", project="demo", agent_id="my-agent")
```

---

## Logging Events

```python
from second_brain import Brain

brain = Brain.default()
brain.init()

brain.log_event(
    type="task_completed",
    title="Deployed API",
    details="Added GET /api/foo and tested",
    project="my-project",
    outcome="passed",
    tags=["api", "deployment"],
    agent_id="agent-1",
    session_id=None,
    meta={"commit": "abc123"},
)
```

---

## Credentials (Encrypted)

```python
from second_brain import Brain

brain = Brain.default()
brain.init()

cred_id = brain.store_credential(
    service="openai",
    kind="api_key",
    context="production",
    value="sk-...",
    rotation_note="rotate monthly",
)

value = brain.get_credential(cred_id)
assert value is not None

# list metadata (never decrypted values)
rows = brain.list_credentials(service="openai")
```

---

## CLI Reference

### Initialize
```bash
second-brain init
```

### Log an event
```bash
second-brain log task_completed "Deploy API" --project my-project --agent agent1 --tag api --details "Endpoints live"
```

### List events
```bash
second-brain events --project my-project --limit 50
second-brain events --failed --limit 20
```

### Credentials
```bash
second-brain credential add openai api_key production
second-brain credential list --service openai
second-brain credential get <cred_id>
```

---

## Optional Server Mode (write-only)

Install:
```bash
pip install 'second-brain[server]'
```

Create a token + run server:
```bash
second-brain init
second-brain server token-create --agent agentA
second-brain server serve --host 0.0.0.0 --port 8009
```

Agent writes events:
```bash
curl -X POST http://localhost:8009/v1/events \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"type":"task_started","title":"hello","project":"demo","tags":["srv"]}'
```

---

## Notes

- Back up `brain.key`. Without it, encrypted credentials cannot be recovered.
- Events are plaintext in SQLite (intentionally) so you can search/filter easily.
- Agent tokens are write-only in v1 (safer default).
