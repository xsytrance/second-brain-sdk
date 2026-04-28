# Second Brain

> Standalone SQLite-backed memory + encrypted credential vault for AI agents.

Second Brain is a **drop-in local “brain”** for any agent framework. It stores:
- **Events** (plaintext) in **SQLite** for fast search/filtering
- **Credentials** (encrypted at rest) using **Fernet** (via `cryptography`)

It also ships with a CLI (`second-brain`) and an optional server extra (`second-brain[server]`) for **write-only agent ingestion**.

---

## Install

```bash
pip install second-brain

# Optional: server mode
pip install 'second-brain[server]'
```

---

## Quick Start (CLI)

```bash
# Uses ~/.second-brain by default (or set SECOND_BRAIN_DIR)
second-brain init

second-brain log task_started "Connect Facebook API" --project nook-polish --agent hermes --tag api --tag backend
second-brain events --limit 20

# Credentials are encrypted at rest
second-brain credential add facebook page_access_token "Nook & Polish Page"   # prompts securely
second-brain credential list
second-brain credential get <cred_id>
```

Set a custom location:
```bash
export SECOND_BRAIN_DIR=~/my-brain
second-brain init
```

---

## Quick Start (Python)

```python
from second_brain import Brain

brain = Brain.default()   # or Brain(Path("/custom/dir"))
brain.init()

event_id = brain.log_event(
    type="task_started",
    title="Connect Facebook API",
    project="nook-polish",
    agent_id="hermes",
    tags=["facebook", "api"],
)
print("event:", event_id)

cred_id = brain.store_credential(
    service="facebook",
    kind="page_access_token",
    context="Nook & Polish Page",
    value="EAAB...",
)
print("cred:", cred_id)

# decrypt only when needed
token = brain.get_credential(cred_id)
```

---

## Storage & Security

### Files on disk
Default directory: `~/.second-brain/`
- `brain.db` 
 SQLite database (events are plaintext)
- `brain.key` 
 Fernet key used to encrypt/decrypt credential values

### Encryption policy (current)
- **Events:** plaintext (searchable)
- **Credentials:** encrypted at rest (`value_enc` stored in SQLite)

**Important:** Back up `brain.key`. If you lose it, encrypted credentials cannot be recovered.

---

## Optional Server Mode (write-only)

Use this if you want other agents to write events **without sharing** your DB file or `brain.key`.

### Start server
```bash
export SECOND_BRAIN_DIR=~/.second-brain
second-brain init

second-brain server token-create --agent agentA --note "remote agent"
second-brain server serve --host 0.0.0.0 --port 8009
```

### Agent writes an event
```bash
curl -X POST http://localhost:8009/v1/events \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"type":"task_started","title":"hello from agent","project":"demo"}'
```

Design choice (safer default): agent tokens are **write-only** in v1 (no read endpoints).

---

## Legacy API

This repo still includes a legacy encrypted-JSON `Vault` API for backwards compatibility during migration.
New projects should use `Brain`.

---

## License
MIT
