# Second Brain SDK

> Event-sourced knowledge base with encrypted credentials for AI agents.

[![PyPI](https://img.shields.io/pypi/v/second-brain-sdk)](https://pypi.org/project/second-brain-sdk/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

```
       🧠
      ╱╲
     ╱__╲
    │  Second Brain SDK  │
    └─────────────────────┘
Everything you do — logged, timestamped, and secured.
```

## What Is This?

Second Brain is a **local, encrypted, event-sourced memory extension** for AI agents. Every action, decision, success, and failure gets logged with a timestamp. Credentials (API keys, passwords, tokens) are stored encrypted with Fernet (AES-128). The entire history is queryable and exportable.

**Inspired by** the need for agents to remember what they did, track progress across sessions, and never lose credentials — while keeping everything private and offline.

## Features

- **📜 Event Sourcing** — every task, decision, milestone is an immutable event
- **🔐 Encrypted Vault** — credentials and sensitive data encrypted with Fernet (AES)
- **🗃️ Session Tracking** — automatic session grouping with start/end timestamps
- **📊 Query Language** — filter events by project, tag, outcome, date range
- **🔍 Credential Manager** — store, retrieve, rotate secrets safely
- **📁 Skill Tracking** — log which reusable workflows you created
- **📤 Export & Backup** — Markdown summaries, JSON dumps, quarterly archives
- **🤖 Hermes Integration** — designed for Hermes Agent, works with any Python agent
- **🖥️ CLI Tool** — inspect vault, list events, add credentials from terminal

## Quick Start

```bash
# Install from PyPI (when published)
pip install second-brain-sdk

# Or install locally
cd second-brain-sdk
pip install -e .

# Initialize your Second Brain
second-brain init

# The vault lives at ~/.hermes/profiles/snow/second_brain/
# The encryption key is at ~/.hermes/profiles/snow/second_brain/decryption_key.key
# ★ BACK UP THE KEY SEPARATELY — vault is unrecoverable without it! ★
```

## Basic Usage

```python
from second_brain_sdk import Vault, Session, CredentialManager

# Point to your brain directory
vault = Vault("~/.hermes/profiles/snow/second_brain/vault.json.enc")

# Log an event
vault.log_event(
    event_type="task_started",
    title="Connect Facebook API",
    project="nook-polish",
    tags=["facebook", "flask", "api"]
)

# Start a session (auto-logs session_start)
session = Session(vault, project="nook-polish")
session.log("task_completed", "Added GET /api/facebook/posts", tags=["backend"])

# Store a credential (encrypted)
creds = CredentialManager(vault)
cred = creds.store(
    service="facebook",
    kind="page_access_token",
    context="Nook & Polish Studio — ID 1019836827871345",
    value="EAANqPNQmmssBRcYhWY8et5Xm..."
)
print(f"Stored credential ID: {cred.id}")

# Retrieve it later
token = creds.retrieve(cred.id)
print(f"Token starts with: {token[:20]}...")

# End session and save summary
summary_path = session.save_summary()
print(f"Session log saved to {summary_path}")

# Query events
recent_failures = Query(vault).failed().limit(5).all()
print(f"Last 5 failures: {recent_failures}")
```

## CLI Reference

```bash
$ second-brain --help
Usage: second-brain [OPTIONS] COMMAND [ARGS]...

Options:
  --brain-dir PATH  Directory containing Second Brain vault
  --help           Show this message and exit.

Commands:
  init              Initialize a new Second Brain
  log               Log an event to the vault
  events            List events from the vault
  stats             Show vault statistics
  credential        Manage encrypted credentials
  summary           Generate session summary
  export            Export entire vault as JSON (decrypted)
  info              Show brain info and identity
```

Examples:
```bash
second-brain log task_started "Build API endpoint" --project myapp --tag api --tag backend
second-brain events --project myapp --failed --limit 10
second-brain credential add facebook page_token "My Page Context" --value <TOKEN>
second-brain credential list --service facebook
second-brain stats
```

## Data Model

### Vault Structure (encrypted on disk)

```json
{
  "version": "1.0",
  "created_at": "2026-04-27T17:25:08Z",
  "events": [
    {
      "id": "evt_abc123",
      "timestamp": "2026-04-27T15:42:13Z",
      "type": "task_completed",
      "title": "Added Facebook Graph API endpoint",
      "details": "Implemented GET /api/facebook/posts...",
      "project": "nook-polish",
      "outcome": "passed",
      "files_changed": ["/path/to/app.py"],
      "tags": ["facebook", "flask", "api"],
      "session_id": "sess_xyz789",
      "next_steps": ["Test publishing endpoint", "Add error handling"]
    }
  ],
  "credentials": [
    {
      "id": "cred_fb_token_123",
      "created_at": "2026-04-27T16:10:00Z",
      "service": "facebook",
      "kind": "page_access_token",
      "context": "Nook & Polish Studio — ID 1019836827871345",
      "encrypted_value": "gAAAAABm...",  // Fernet-encrypted
      "last_used": "2026-04-27T17:05:23Z",
      "expires_at": null,
      "rotation_note": "Rotate every 60 days"
    }
  ],
  "skills_created": [
    {
      "name": "facebook-graph-api-bridge-flask",
      "created_at": "2026-04-27T18:30:00Z",
      "category": "devops",
      "path": "devops/facebook-graph-api-bridge-flask/SKILL.md",
      "purpose": "Direct Facebook Graph API integration...",
      "status": "active"
    }
  ],
  "identity": {
    "agent": {
      "name": "Hermes",
      "personality_traits": ["warm", "feminine", "protective"],
      "specialization": "assistant-for-Snooky"
    },
    "user": {
      "name": "Snooky Gomez",
      "alias": "Snow",
      "location": "Bacolod, Philippines",
      "current_focus": ["Nook & Polish", "K-1 visa"]
    }
  }
}
```

### Event Types

| Type | Meaning |
|------|---------|
| `task_started` | Began work on something |
| `task_completed` | Finished successfully |
| `task_failed` | Hit a blocker (error logged) |
| `decision` | Important choice recorded with reasoning |
| `milestone` | Major achievement reached |
| `credential_added` | New API key/password stored |
| `credential_rotated` | Secret replaced (old one retired) |
| `skill_created` | Reusable workflow saved |
| `session_start` | Conversation begun |
| `session_end` | Conversation ended (summary generated) |

## Encryption

Uses **Fernet** (AES-128 in CBC mode with HMAC-SHA256) from `cryptography`.

**Key storage:**
- Key saved separately as `decryption_key.key`
- Never commit this to Git!
- Back it up externally (USB drive, password manager, cloud key vault)
- Rotate annually: decrypt all, generate new key, re-encrypt all

**Rotating the key:**
```bash
second-brain rotate-key --old-key /path/to/old.key --new-key /path/to/new.key
```

## Session Auto-Logging (Hermes Integration)

Wrap your agent's main loop:

```python
from second_brain_sdk import Vault, Session

brain = Vault("~/.hermes/profiles/snow/second_brain/vault.json.enc")
session = Session(brain, project="current-work")

# Inside your agent's turn:
with session.task(title="Process user request", tags=["nlp"]):
    # ... do work ...
    if something_failed:
        session.log("task_failed", title="...", error=str(e))
    else:
        session.log("task_completed", title="...")
        session.milestone("Feature deployed", "API is live!")

# At end of conversation:
summary_md = session.end("All goals met")
print(summary_md)
```

Or use the decorator pattern:

```python
@session.task_wrapper
def handle_request(request):
    # automatically logs start/completion/failure
    ...
```

## Query Examples

```python
from second_brain_sdk import Query, Vault
vault = Vault(...)

# Recent failures
fails = Query(vault).failed().since("2026-04-27").limit(10).all()

# All events for a project
project_events = Query(vault).project("nook-polish").all()

# Milestones this week
milestones = Query(vault).tag("milestone").since("2026-04-21").all()

# Count passed tasks per project
from collections import Counter
passed = Query(vault).passed().all()
Counter(e["project"] for e in passed)
```

## Directory Layout

After `second-brain init`:

```
~/.hermes/profiles/snow/second_brain/
├── vault.json.enc              # Encrypted master store (all events + creds)
├── decryption_key.key          # Fernet key — BACK THIS UP!
├── config.yaml                 # Settings (retention, export schedule)
├── identity.json               # Agent + user identity (plaintext for quick load)
├── index.md                    # Human-readable timeline (links to sessions)
└── sessions/
    ├── 2026-04-27_1527_session_abc123.md
    └── ...
```

## Security Best Practices

1. **Never log raw secrets** — always use `credential_manager.store()` which encrypts
2. **Back up the key** — store `decryption_key.key` in a separate location from the vault
3. **Rotate credentials** — set `rotation_note` to remind yourself to refresh API keys
4. **Restrict file permissions** — `chmod 600` on `decryption_key.key` and `vault.json.enc`
5. **Audit regularly** — run `second-brain events --tag credential_added` to review secret additions

## Use Cases

- **Agent memory across sessions** — remember what you did last week
- **Audit trail** — who did what, when, and why (for debugging)
- **Credential vault** — API keys, passwords, tokens encrypted at rest
- **Progress tracking** — see tasks completed over time
- **Decision log** — why did we choose Graph API over Zapier? Now you know
- **Skill inventory** — which reusable workflows have we built?
- **Session summaries** — auto-generated recaps of every conversation

## Installation for Development

```bash
git clone https://github.com/yourusername/second-brain-sdk.git
cd second-brain-sdk
pip install -e ".[dev]"
pre-commit install  # optional: hooks for formatting
```

Run tests:
```bash
pytest tests/ -v
```

## Publishing to PyPI

```bash
# Build
python -m build

# Upload (requires twine)
twine upload dist/*
```

## Contributing

Contributions welcome! Please:
- Add tests for new features
- Run `black` and `isort` for formatting
- Update README with usage examples
- Keep backward compatibility (semver)

## License

MIT — see [LICENSE](LICENSE) for details.

## Credits

Built for **Hermes Agent** by Nous Research, inspired by Snooky's need to track everything she builds — from Facebook API bridges to ComfyUI image generators.

---

**Ready to build your second brain?** Run `second-brain init` and start logging! 🧠✨
