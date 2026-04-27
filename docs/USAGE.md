# Second Brain SDK — Usage Guide

## Table of Contents

1. [Quick Start](#quick-start)
2. [Logging Events](#logging-events)
3. [Session Management](#session-management)
4. [Credentials](#credentials)
5. [Querying](#querying)
6. [CLI Reference](#cli-reference)
7. [Best Practices](#best-practices)
8. [Integration Patterns](#integration-patterns)

---

## Quick Start

```python
from second_brain_sdk import Vault

# Point to your encrypted vault
vault = Vault("~/.hermes/prof/snow/second_brain/vault.json.enc")

# Log something
vault.log_event("milestone", "First event logged", project="demo")
```

---

## Logging Events

Events are the core data structure. Every meaningful action should be an event.

```python
from second_brain_sdk import Vault

vault = Vault(...)

# Simple event
vault.log_event(
    event_type="task_completed",
    title="Deployed Facebook API",
    details="Added GET /api/facebook/posts and tested with page token",
    project="nook-polish",
    tags=["facebook", "flask", "deployment"],
    files_changed=["/home/user/site/app.py"],
    next_steps=["Add POST endpoint", "Set up monitoring"],
)
```

**Event type reference:**

- `task_started` — you began work
- `task_completed` — finished successfully
- `task_failed` — hit an error (include `error` field)
- `decision` — made a choice (include reasoning)
- `milestone` — big achievement (e.g., "API live!")
- `credential_added` — stored a new secret
- `credential_rotated` — replaced a secret
- `skill_created` — saved a reusable workflow
- `session_start` / `session_end` — automatically logged by `Session`

---

## Session Management

Session tracks a single conversation or work session.

```python
from second_brain_sdk import Vault, Session

vault = Vault(...)

# Start session
session = Session(vault, project="Nook & Polish - May Update")

# Log within session (session_id auto-added)
session.log("task_started", "Review Facebook analytics")
session.log("task_completed", "Top post: 150 engagements")

# Use context manager for auto-logging
with session.task("Generate promo image", tags=["comfyui", "marketing"]):
    # do work...
    result = generate_image(...)
    # if exception occurs → task_failed logged automatically
    # if exit normally → task_completed logged

# End session and get summary
summary_md = session.end("All tasks finished. Ready for next sprint.")
print(summary_md)

# Save to file
filepath = session.save_summary()  # saved to sessions/
```

---

## Credentials

```python
from second_brain_sdk import Vault, CredentialManager

vault = Vault(...)
creds = CredentialManager(vault)

# Store (encrypted)
cred = creds.store(
    service="facebook",
    kind="page_access_token",
    context="Nook & Polish Studio — ID 1019836827871345",
    value="EAANqPNQmmssBRcYhWY8et5Xm5h1...",
    rotation_note="Rotate every 60 days",
)
print(f"Stored as {cred.id}")

# Retrieve (decrypted)
token = creds.retrieve(cred.id)
print(f"Token: {token[:20]}...")

# Mark as used (audit)
creds.mark_used(cred.id)

# Rotate (replace with new value, old one retired)
new_cred = creds.rotate(
    cred_id=cred.id,
    new_value="NEW_TOKEN_HERE",
    reason="Scheduled 60-day rotation"
)
```

**Credential metadata fields:**
- `service` — e.g., "facebook", "openai", "aws"
- `kind` — e.g., "page_access_token", "api_key", "password"
- `context` — human-readable explanation of where it's used
- `expires_at` — optional ISO date for expiry reminders
- `rotation_note` — when/why to rotate

---

## Querying

```python
from second_brain_sdk import Query, Vault

vault = Vault(...)

# Basic filters
Query(vault).project("my-project").all()           # by project
Query(vault).tag("facebook").all()                # any tag match
Query(vault).outcome("failed").all()              # only failures
Query(vault).type("task_completed").all()         # by event type

# Chained
Query(vault).project("nook-polish").tag("api").passed().all()

# Date range
Query(vault).since("2026-04-27").until("2026-04-28").all()

# Limit
Query(vault).failed().limit(5).all()

# Preset queries
Query.recent_failures(vault, hours=24)      # failures in last 24h
Query.by_project(vault, "nook-polish")     # all events for project
Query.milestone_timeline(vault)            # all milestones sorted chronologically

# Single result
first = Query(vault).project("demo").first()
if first:
    print(first["title"])
```

---

## CLI Reference

### Initialize
```bash
second-brain init
```
Creates vault, key, config, and directories.

### Log an Event
```bash
second-brain log task_completed \
  "Deploy Facebook API" \
  --project nook-polish \
  --tag api --tag deployment \
  --details "Endpoints live and tested" \
  --file /path/to/app.py
```

### List Events
```bash
second-brain events --project nook-polish --failed --limit 20
second-brain events --tag facebook --since 2026-04-27
```

### Show Stats
```bash
second-brain stats
```

### Credentials
```bash
second-brain credential add facebook page_token "Nook & Polish" \
  --value <paste-token-here>

second-brain credential list --service facebook

second-brain credential get cred_abc123def456  # shows decrypted value

second-brain credential rotate cred_abc123def456 \
  --new-value "NEW_TOKEN"
```

### Session Summary
```bash
second-brain summary   # latest session as markdown
```

### Export
```bash
second-brain export    # full vault as JSON (DANGER: unencrypted!)
```

### Info
```bash
second-brain info      # vault path, stats, identity
```

---

## Best Practices

1. **Always use sessions** — wrap work in `Session()` for automatic grouping
2. **Tag everything** — `#facebook`, `#flask`, `#docker` — makes querying easy
3. **Log decisions** — use `session.decision()` with reasoning and alternatives
4. **Encrypt all secrets** — never log raw API keys; use `CredentialManager.store()`
5. **Back up the key** — copy `decryption_key.key` to external storage monthly
6. **Rotate credentials** — set `rotation_note="Rotate every 60 days"` and set calendar reminder
7. **Review failures weekly** — `second-brain events --failed` to spot recurring issues
8. **Keep skill docs updated** — when you create a new `.md` skill, call `vault.register_skill()`

---

## Integration Patterns

### Hermes Agent Auto-Logging

Create a middleware that wraps each agent turn:

```python
from second_brain_sdk import Vault, Session

# Load at agent startup
vault = Vault.from_env()  # reads SECOND_BRAIN_DIR
session = Session(vault, project=current_project)

def agent_turn(user_message: str):
    with session.task(title=f"Respond to: {user_message[:50]}", tags=["conversation"]):
        response = generate_response(user_message)
        # auto-logs completion or failure
    return response

# On disconnect:
session.end("Conversation ended")
```

### Git Hook (Post-Commit)

```bash
# .git/hooks/post-commit
second-brain log git_commit \
  "Commit: $(git log -1 --oneline)" \
  --files "$(git diff-tree --no-commit-id --name-only -r HEAD)"
```

### Cron Job (Daily Digest)

```python
from second_brain_sdk import Query, Vault
vault = Vault(...)

yesterday = (datetime.now() - timedelta(days=1)).isoformat()
events = Query(vault).since(yesterday).all()

# Send email summary or post to Slack
```

---

**Your second brain is ready. Start logging!** 🧠✨
