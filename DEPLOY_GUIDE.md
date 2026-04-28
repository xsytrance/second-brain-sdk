# SECOND BRAIN — AGENT DEPLOYMENT GUIDE
**Purpose:** Install and configure Second Brain on any VG Clan agent (Hermes, HeartMuLa, VENUS, PLUTO, VPS).  
**Audience:** Operator (you) or any teammate.  
**Time per node:** ~5 minutes.  
**Last updated:** 2026-04-28  

---

## 1. BEFORE YOU START — Prerequisites

On the target agent node, confirm:

| Check | Command | Expected |
|-------|---------|----------|
| Python ≥ 3.9 available | `python3 --version` | `Python 3.9` or higher |
| Venv support | `python3 -m venv --help` | shows usage, no error |
| Git available | `which git` | `/usr/bin/git` or similar |
| Network to PRIME (server mode) | `curl -s http://100.104.159.48:8009/health` | `{"ok":true}` (after PRIME server started) |
| SSH access (from PRIME) | `ssh <node> echo ok` | `ok` |

---

## 2. INSTALLATION — 5 MINUTES (Standard Venv)

Run on **target agent node**:

```bash
# 1. Clone repo
git clone https://github.com/xsytrance/second-brain-sdk.git ~/second-brain-sdk
cd ~/second-brain-sdk

# 2. Create/activate virtual environment
python3 -m venv ~/.venvs/second-brain
source ~/.venvs/second-brain/bin/activate

# 3. Install package (editable + server extra for HTTP mode if needed)
pip install -e .[server]

# 4. Initialize brain directory
second-brain init

# 5. Verify
second-brain status
```

**Success:** `second-brain status` shows DB size, event count, no errors.

---

## 3. MODES — Local vs Server

### Mode A: Local-Only (default)
Each agent writes to its own `~/.second-brain/brain.db`. No extra config.

**Use when:** agent is standalone; no need for central aggregation.

---

### Mode B: Central Server (recommended)

**On PRIME (server):**
```bash
# Create token for each remote agent
second-brain server token-create --agent venus-worker --note "VENUS collector"
second-brain server token-create --agent pluto-scout --note "PLUTO sensors"
# COPY TOKENS SECURELY (shown once)

# Start server (foreground test)
second-brain server serve --host 127.0.0.1 --port 8009
# Ctrl+C to stop

# Verify
curl http://127.0.0.1:8009/health  # {"ok":true}

# (Production) Install systemd user service
cp ~/second-brain-sdk/deploy/systemd/second-brain.service ~/.config/systemd/user/
loginctl enable-linger $USER
systemctl --user daemon-reload
systemctl --user enable --now second-brain
systemctl --user status second-brain
```

**On remote agent (VENUS, PLUTO, etc.):**
```bash
# Already installed via Step 2 above

# Configure server URL + token
echo 'export SECOND_BRAIN_SERVER_URL="http://100.104.159.48:8009"' >> ~/.bashrc
echo 'export SECOND_BRAIN_TOKEN="tok_..."' >> ~/.bashrc
source ~/.bashrc

# Test write
curl -X POST "$SECOND_BRAIN_SERVER_URL/v1/events" \
  -H "Authorization: Bearer $SECOND_BRAIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"type":"heartbeat","title":"test","project":"vg-clan"}'

# On PRIME, verify:
second-brain events --agent venus-worker --limit 1
```

---

## 4. AGENT-SPECIFIC INTEGRATIONS

### Hermes (PRIME)
Plugin auto-logs. After install:
1. Confirm plugin: `ls ~/.hermes/plugins/second_brain/plugin.py`
2. Config in `~/.hermes/config.yaml`: `plugins.enabled: [second_brain]`
3. Restart: `hermes restart` or `systemctl --user restart hermes`
4. Check logs: `journalctl --user -u hermes -f | grep second_brain`
5. Test: send message in Hermes → `second-brain events --agent hermes --limit 5`

---

### HeartMuLa (MusicGen)
Manual wrapper needed. Example:

```python
from second_brain import Brain
brain = Brain.default(); brain.init()
sid = brain.start_session(agent_id="heartmula", project="music")
try:
    # ... existing generation logic ...
    brain.log_event(type="task_completed", title="Beat generated", session_id=sid)
finally:
    brain.end_session(sid)
```

See `examples/agent_workflow.py`.

---

### Generic Python / Cron
Add session lifecycle around your script (see Section 5.3 in full capabilities report).

---

## 5. POST-INSTALL CHECKLIST

- [ ] `second-brain init` completed
- [ ] `second-brain status` works
- [ ] Test event logged (`second-brain log test …`)
- [ ] Session start/end works (`session-start` / `session-end`)
- [ ] Plugin loaded (Hermes only): check for `[second_brain] plugin loaded` in logs
- [ ] If server mode: health endpoint returns `{"ok":true}`
- [ ] Permissions: `chmod 600 ~/.second-brain/brain.key`
- [ ] Key backed up (PRIME): `scp ~/.second-brain/brain.key xsyvps@vps:~/backups/prime_brain_key_$(date +%Y%m%d).key`

---

## 6. ONGOING OPS

### Daily
- Backup brain.db + brain.key to VPS (PRIME only)
- `second-brain status` (quick health)

### Weekly
- Review failed events: `second-brain events --failed --limit 20`
- Check DB size: `du -h ~/.second-brain/brain.db`

### Monthly
- Retention: `second-brain prune --days 90`
- Token audit: `second-brain server token-list` (revoke unused)

### Monitoring
Add to crontab:
```bash
*/5 * * * * /home/xsyprime/second-brain-sdk/scripts/health_check.py || echo "SB down on $(hostname)" | mail -s "ALERT" agenor@outlook.com
```

---

## 7. TROUBLESHOOTING

| Problem | Quick Fix |
|---------|-----------|
| `ModuleNotFoundError` | Activate correct venv; `pip install second-brain` |
| FK constraint error | Upgrade DB: delete brain.db and re-run `second-brain init` (data loss) — or use DEFERRABLE from this fork |
| No events from Hermes | Check `plugins.enabled` in `~/.hermes/config.yaml`; restart Hermes |
| DB locked | Stop other writers; enable WAL (default); use server mode for concurrent writers |
| 401 from server | Token wrong/revoked — recreate on server, update agent env |
| `brain.key` lost | Restore from backup; else credentials unrecoverable |

Full troubleshooting: `docs/TROUBLESHOOTING.md` in repo.

---

## 8. QUICK COMMAND REF

```bash
second-brain init                          # first-time setup
second-brain status                        # health + stats
second-brain log <type> "<title>" [opts]   # manual event
second-brain events [filters]              # query
second-brain session-start --agent X --project Y
second-brain session-end <session_id>
second-brain prune --days 90               # retention
second-brain server token-create --agent X  # server mode
second-brain server serve --port 8009      # start server
```

---

**Next:** Deploy to VENUS, PLUTO, VPS using this same guide.  
**Docs:** `~/second-brain-sdk/docs/`  
**Scripts:** `~/second-brain-sdk/scripts/`  
**Systemd:** `~/second-brain-sdk/deploy/systemd/`

