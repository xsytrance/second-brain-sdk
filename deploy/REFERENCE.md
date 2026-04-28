# Second Brain — Multi-Agent Deployment Reference

This document is the canonical source of truth for installing, configuring, and operating Second Brain across all VG Clan nodes (PRIME, VPS, VENUS, PLUTO, and future agents).

---

## Node Inventory

| Node | Role | Second Brain Role | Install Path | Service? |
|------|------|-------------------|--------------|----------|
| **PRIME** | Command & Control | Primary brain (Hermes integration) | `~/.second-brain` | On-demand (Hermes plugin uses local DB) |
| **VPS** | External exposure | Optional write-through cache or backup brain | TBD | Optional |
| **VENUS** | Masterdrive host | Local event store, feeds PRIME | TBD | Optional |
| **PLUTO** | Staging / CPU-only | Lightweight event forwarder | TBD | Optional |

---

## Installation Matrix

### Hermes Agent (PRIME)

Hermes is the primary consumer. Plugin auto-logs.

```bash
# Already done — reference only
source ~/.hermes/hermes-agent/venv/bin/activate
pip install second-brain
second-brain init

# Plugin installed at:
cp -r ~/second-brain-sdk/integrations/hermes ~/.hermes/plugins/second_brain

# Config already in ~/.hermes/config.yaml:
# plugins:
#   enabled:
#     - second_brain

# Restart Hermes
hermes restart  # or systemctl --user restart hermes
```

**Verification:**
```bash
second-brain events --limit 5  # should show session_started after next chat
```

---

### HeartMuLa (MusicGen worker on PRIME)

HeartMuLa runs in `/home/xsyprime/ai/heartlib/.venv`. Optional logging.

```bash
source /home/xsyprime/ai/heartlib/.venv/bin/activate
pip install second-brain

# Initialize brain (can share PRIME's brain or separate)
export SECOND_BRAIN_DIR=~/.second-brain-heartmula  # optional separate
second-brain init

# Instrument: wrap HeartMuLa generation function
# In your generation script:
from second_brain import Brain
brain = Brain.default()
brain.init()
sid = brain.start_session(agent_id="heartmula", project="music")

try:
    # ... existing generation logic ...
    brain.log_event(type="task_completed", title="Beat generated", session_id=sid, meta={"duration": "...", "model": "musicgen-small"})
finally:
    brain.end_session(sid)
```

**Uninstrumented HeartMuLa won't auto-log** — requires manual wrapper.

---

### Future: OpenCode / Claude Code (if added)

These CLI agents support Python plugins or wrapper scripts.

**Option A — Wrapper script** (`~/.local/bin/opencode-with-brain`):
```bash
#!/bin/bash
export SECOND_BRAIN_SERVER_URL="http://prime:8009"  # or local
source /path/to/opencode/venv/bin/activate
python -m opencode_wrapper "$@"
```

**Option B — Direct SDK in agent's Python code** (if agent allows custom modules).

---

### Remote Node Agent (VENUS, PLUTO)

If VENUS/PLUTO run autonomous agents that need to log:

**Step 1 — Install package:**
```bash
ssh venus "python3 -m venv ~/.venvs/second-brain && source ~/.venvs/second-brain/bin/activate && pip install second-brain[server] && second-brain init"
```

**Step 2 — Get token from PRIME:**
```bash
# On PRIME
second-brain server token-list
# Copy token for venus-worker
```

**Step 3 — Configure environment on remote:**
```bash
ssh venus "echo 'export SECOND_BRAIN_SERVER_URL=http://prime:8009' >> ~/.bashrc"
ssh venus "echo 'export SECOND_BRAIN_TOKEN=tok_...' >> ~/.bashrc"
```

**Step 4 — Test POST:**
```bash
ssh venus "source ~/.bashrc && python3 -c 'import requests; requests.post("$SECOND_BRAIN_SERVER_URL/v1/events", headers={"Authorization": f"Bearer $SECOND_BRAIN_TOKEN"}, json={"type":"heartbeat","title":"venus up"})'"
```

**Step 5 — (Optional) Install as systemd on remote:**
```bash
ssh venus "mkdir -p ~/.config/systemd/user"
scp deploy/systemd/second-brain.service venus:~/.config/systemd/user/
ssh venus "systemctl --user daemon-reload && systemctl --user enable --now second-brain"
```

---

## Server Modes

### Mode 1: Local-Only (default)
- Each agent writes to its own `~/.second-brain/brain.db`
- Pros: isolation, no network dependency
- Cons: fragmented, no central view

### Mode 2: Central Server (recommended for VG Clan)
- PRIME runs server: `second-brain server serve --host 0.0.0.0 --port 8009`
- All other agents POST to it via `SECOND_BRAIN_SERVER_URL`
- Pros: unified timeline, single backup point
- Cons: single point of failure (mitigate with systemd auto-restart)

### Mode 3: Hybrid
- Each node runs local server + replicator (future feature)
- Events fan-out to multiple brains

---

## Token Management

Tokens are write-only, one per agent.

```bash
# List
second-brain server token-list

# Create
second-brain server token-create --agent venus-worker --note "data collector"

# Revoke
second-brain server token-revoke tok_...

# View token value (only shown on creation — store elsewhere!)
# second-brain server token-show <id>  # future
```

**Token storage on remote nodes:** add to agent's systemd service file:
```
Environment="SECOND_BRAIN_TOKEN=tok_..."
```

Or use a credential manager (HashiCorp Vault, 1Password) — but tokens themselves are write-only, so exposure risk is low.

---

## Backup & Recovery

### What to back up
- **`~/.second-brain/brain.db`** — all events (plaintext, safe to store)
- **`~/.second-brain/brain.key`** — encryption key (KEEP SECRET; needed for credential decryption)
- **API tokens** — stored in DB, recoverable from `api_tokens` table if DB backed up

### Backup schedule
```bash
# On PRIME (daily)
0 2 * * * scp ~/.second-brain/brain.db xsyvps@vps:/home/xsyvps/backups/prime_brain_$(date +\%Y\%m\%d).db
0 3 * * * scp ~/.second-brain/brain.key xsyvps@vps:/home/xsyvps/backups/prime_brain_key_$(date +\%Y\%m\%d).key
```

### Restore
```bash
scp backups/prime_brain_20260428.db ~/.second-brain/brain.db
scp backups/prime_brain_key_20260428.key ~/.second-brain/brain.key
chmod 600 ~/.second-brain/brain.key
second-brain status  # verify
```

---

## Monitoring & Alerts

### Health check
Use `scripts/health_check.py`:
```bash
python3 ~/second-brain-sdk/scripts/health_check.py
# Exit 0 = OK, 1 = degraded
```

Cron for monitoring:
```bash
*/5 * * * * /home/xsyprime/second-brain-sdk/scripts/health_check.py || echo "Second Brain down" | mail -s "ALERT" agenor@outlook.com
```

### Metrics to watch
- DB size: `SELECT pg_size_pretty(pg_database_size('brain'));` — actually SQLite: `du -h ~/.second-brain/brain.db`
- Events rate: `SELECT COUNT(*) FROM events WHERE ts > datetime('now','-1 hour')`
- Token usage: `SELECT agent_id, COUNT(*) FROM api_tokens JOIN events ...` — future enhancement
- Failed events: `SELECT COUNT(*) FROM events WHERE outcome='failed'`

---

## Security Checklist

- [x] `brain.key` backed up offsite (VPS) — done
- [x] Permissions: `chmod 700 ~/.second-brain; chmod 600 ~/.second-brain/brain.key`
- [ ] Principle of least privilege — are all agents using tokens with only `events:write`? (verify)
- [ ] Server behind firewall — bind to `127.0.0.1` unless reverse-proxied
- [ ] Rotate tokens quarterly or on node compromise
- [ ] Audit `events` table for PII (avoid logging secrets inadvertently)
- [ ] Enable HTTPS for server (nginx + Let's Encrypt) if exposed externally

---

## Troubleshooting by Node

### PRIME (Hermes)
- Plugin not loading? Check `~/.hermes/config.yaml` → `plugins.enabled`
- Events not appearing? Ensure `second-brain init` ran in Hermes venv
- Conflicting DB locks? Only one writer at a time; WAL mitigates but not for heavy concurrent writes

### VPS (exposed server)
- Port 8009 blocked? Check UFW/iptables: `ufw allow 8009`
- Token rejected? Verify token in `api_tokens` table not revoked
- High memory? FastAPI default workers = 1; consider `--workers 4` if needed

### VENUS / PLUTO (future)
- Cannot resolve PRIME hostname? Use IP: `SECOND_BRAIN_SERVER_URL=http://100.104.159.48:8009`
- DB locked on PRIME? PRIME server serializes requests; queueing happens at FastAPI level

---

## Upgrade Path

When new SDK version released:

```bash
# On each node
source <agent venv>/bin/activate
pip install --upgrade second-brain

# If schema changed, re-init (careful):
# second-brain migrate up   # future command
# OR: back up DB, delete brain.db, second-brain init (loses events)
```

**Upgrade strategy:** migrations added in `docs/SCHEMA_MIGRATIONS.md`. Auto-migration planned for v1.0.

---

## Contact

Questions? File an issue on GitHub or ping `xsytrance` in VG Clan.

