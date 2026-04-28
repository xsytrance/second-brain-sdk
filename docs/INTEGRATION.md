# Agent Integration Guide

Second Brain is designed to be aDrop-in memory layer for any AI agent or framework. This guide covers patterns for Python agents (direct API) and framework-specific integrations (Hermes, OpenCode, Claude Code, etc.).

---

## Core Concepts

### Events vs Sessions

- **Event**: A single logged occurrence (e.g., `task_started`, `tool_called`, `milestone`). Stored plaintext for search.
- **Session**: A logical conversation or run. Groups related events under one `session_id`. Optional but highly recommended for multi-turn agents.

**Important:** If you provide a `session_id` when logging an event, the session must exist first (created via `start_session`). The foreign-key constraint is enforced, but it's DEFERRABLE so you can create the session and events in the same transaction if needed.

### Recommended Event Taxonomies

For maximum queryability, standardize your event types:

| Category | Types |
|----------|-------|
| Task lifecycle | `task_started`, `task_completed`, `task_failed`, `milestone` |
| LLM reasoning | `llm_call`, `llm_response`, `plan_created`, `plan_updated` |
| Tools & actions | `tool_invocation`, `tool_result`, `file_read`, `file_write` |
| User interaction | `user_message`, `user_feedback`, `user_approval` |
| Agent health | `error`, `warning`, `info`, `heartbeat` |
| Credentials | `credential_accessed`, `credential_rotated` |

---

## Python (Direct SDK Usage)

Install the SDK:

```bash
pip install second-brain
```

Initialize a brain (creates `~/.second-brain/brain.db` and key):

```python
from second_brain import Brain

brain = Brain.default()
brain.init()
```

### Basic event logging

```python
brain.log_event(
    type="task_started",
    title="Deploy to production",
    project="infra",
    agent_id="hermes",
    tags=["deploy", "production"]
)
```

### Sessions

```python
# Start a session
sid = brain.start_session(agent_id="hermes", project="vg-clan")

# Log events within session
brain.log_event(type="task_started", title="Refactor auth", session_id=sid)

# End the session (logs a session_ended event automatically)
brain.end_session(sid, outcome="passed")
```

### Context manager pattern

```python
from second_brain import Brain

brain = Brain.default()
brain.init()

with brain.session(agent_id="worker-1", project="data-pipeline") as sid:
    brain.log_event(type="task_started", title="ETL job", session_id=sid)
    # ... do work ...
    brain.log_event(type="task_completed", title="ETL job", session_id=sid)
# session automatically ended on exit
```

---

## Hermes Agent Integration

Hermes ships with a plugin system. The official Second Brain plugin is included in this repo under `integrations/hermes/plugin.py`. It automatically logs:

- Session start/end per conversation
- Tool calls and results
- LLM requests and responses

### Installation

1. Copy the plugin to your Hermes plugins directory:
   ```bash
   mkdir -p ~/.hermes/plugins
   cp -r ~/second-brain-sdk/integrations/hermes ~/.hermes/plugins/second_brain
   ```

2. Install Second Brain in Hermes's virtual environment:
   ```bash
   # Activate Hermes venv first
   source ~/.hermes/hermes-agent/venv/bin/activate
   pip install second-brain
   pip install 'second-brain[server]'  # optional: for remote ingestion
   ```

3. Initialize the brain:
   ```bash
   second-brain init
   ```

4. (Optional) Run in server mode if you want remote agents to POST events:
   ```bash
   second-brain server token-create --agent hermes --note "Hermes on PRIME"
   second-brain server serve --host 127.0.0.1 --port 8009 &
   ```
   Then set environment variables:
   ```bash
   export SECOND_BRAIN_SERVER_URL="http://127.0.0.1:8009"
   export SECOND_BRAIN_TOKEN="tok_..."
   ```

5. Restart Hermes. The plugin loads automatically from `~/.hermes/plugins/second_brain/`.

### Configuration

| Environment Variable | Purpose |
|---------------------|---------|
| `SECOND_BRAIN_DIR` | Override default brain location (`~/.second-brain`) |
| `SECOND_BRAIN_SERVER_URL` | POST to remote server instead of local DB |
| `SECOND_BRAIN_TOKEN` | Bearer token for server ingestion |
| `HERMES_SECOND_BRAIN_AUTO_SESSION` | Set `false` to disable automatic session creation (default: `true`) |

### What gets logged

Every Hermes conversation becomes a Second Brain session. Each LLM turn, tool call, and result is an event with the session ID attached. Example query:

```bash
second-brain events --agent hermes --limit 20
second-brain events --session <session_id> --tail
```

---

## OpenCode / Claude Code Integration

These agents also support custom plugins. The general pattern:

```python
# In your agent's startup/shutdown hooks:
from second_brain import Brain

brain = Brain.default()
brain.init()

# On each task start:
session_id = brain.start_session(agent_id="opencode", project=os.getenv("PROJECT"))

try:
    # Your agent's logic here
    brain.log_event(type="task_started", title=task_name, session_id=session_id)
    # ... on each LLM call: brain.log_event(type="llm_call", ...)
finally:
    brain.end_session(session_id, outcome="passed" if success else "failed")
```

See `examples/agent_workflow.py` for a minimal runnable example.

---

## Server Mode — Remote Write-Only Ingestion

Run Second Brain as a FastAPI server to allow remote agents to write without direct DB access.

```bash
pip install 'second-brain[server]'
second-brain init
second-brain server token-create --agent remote-worker-1
second-brain server serve --host 0.0.0.0 --port 8009
```

Agents POST to `/v1/events`:

```python
import requests

requests.post(
    "http://brain-host:8009/v1/events",
    headers={"Authorization": f"Bearer {TOKEN}"},
    json={
        "type": "task_started",
        "title": "Remote task",
        "project": "remote",
        "tags": ["api"]
    }
)
```

**Security**: Tokens are write-only (scoped to `events:write`). HTTPS + reverse proxy recommended for production.

---

## Troubleshooting

### FOREIGN KEY constraint failed

**Symptom**: `sqlite3.IntegrityError: FOREIGN KEY constraint failed` when calling `brain.log_event(session_id=...)`.

**Cause**: The referenced session does not exist.

**Fix**: Create a session first:
```python
sid = brain.start_session(agent_id="my-agent", project="demo")
brain.log_event(..., session_id=sid)
```

The foreign key is now **DEFERRABLE** (since v0.2.0), so you can insert session and events in the same transaction without ordering constraints as long as you commit only after both are inserted.

### Brain not initialized

Ensure `brain.init()` is called at startup (or use `Brain.default().init()`). The SDK initializes automatically on most operations, but explicit init is best for clarity.

### Token missing or invalid (server mode)

Check token created:
```bash
second-brain server token-list
```

Verify token is not revoked. Server logs will show 401 errors.

---

## Contributing an Integration

Want to add support for another agent framework (AutoGPT, CrewAI, etc.)?

1. Fork this repo and add your plugin under `integrations/<framework>/`.
2. Follow the plugin template pattern: create `plugin.py` with a `register()` function returning a dict of lifecycle hooks.
3. Add documentation to `docs/INTEGRATION.md`.
4. Open a PR.

