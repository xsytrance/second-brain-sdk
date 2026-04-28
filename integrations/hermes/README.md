# Hermes × Second Brain Plugin

Drop-in Hermes plugin that streams all agent activity into a Second Brain (local or remote).

## What it does

- Creates a session for each Hermes conversation
- Logs LLM calls & responses
- Logs all tool invocations & results
- Auto-ends session on conversation finish

## Installation

### 1. Install Second Brain

```bash
# In Hermes venv
source ~/.hermes/hermes-agent/venv/bin/activate
pip install second-brain
pip install 'second-brain[server]'   # optional, for remote ingestion
```

Initialize brain:
```bash
second-brain init
```

### 2. Deploy the plugin

```bash
# From second-brain-sdk repo root
mkdir -p ~/.hermes/plugins
cp -r integrations/hermes ~/.hermes/plugins/second_brain
```

Directory structure:
```
~/.hermes/plugins/second_brain/
└── plugin.py    ← this file
```

Hermes auto-discovers plugins in `~/.hermes/plugins/<name>/plugin.py`.

### 3. (Optional) Run server mode

If you prefer a write-only HTTP server instead of direct DB access:

```bash
second-brain server token-create --agent hermes
second-brain server serve --host 127.0.0.1 --port 8009 &
export SECOND_BRAIN_SERVER_URL="http://127.0.0.1:8009"
export SECOND_BRAIN_TOKEN="tok_..."
```

### 4. Restart Hermes

Plugin loads on startup. Check logs for:
```
[PLUGIN] second_brain: loaded — logging to /home/xsyprime/.second-brain
```

## Configuration

| Env var | Default | Description |
|---------|---------|-------------|
| `SECOND_BRAIN_DIR` | `~/.second-brain` | Brain directory |
| `SECOND_BRAIN_SERVER_URL` | (none) | Remote server URL (enables HTTP mode) |
| `SECOND_BRAIN_TOKEN` | (none) | Bearer token for remote server |
| `HERMES_SECOND_BRAIN_AUTO_SESSION` | `true` | Auto-create sessions on conversation start |

## Querying your logs

```bash
# Latest events from Hermes
second-brain events --agent hermes --limit 20

# Drill into a specific session
second-brain events --session <session_id>

# See credential accesses
second-brain events --type credential_accessed

# List sessions
second-brain session-list
```

## Developing / Debugging

Enable plugin debug logging:
```bash
export HERMES_PLUGIN_LOG=second_brain:DEBUG
```

Force-reload plugin without restarting Hermes:
```bash
touch ~/.hermes/plugins/second_brain/plugin.py   # some versions watch for changes
```

## Uninstall

```bash
rm -rf ~/.hermes/plugins/second_brain
# optionally: pip uninstall second-brain
```

