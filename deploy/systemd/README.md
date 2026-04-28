# Deployment Guide — Second Brain Server

This covers deploying the Second Brain HTTP server on VG Clan nodes (PRIME, VPS, VENUS, PLUTO) for multi-agent write-only ingestion.

## Quick Deploy (any node)

```bash
# 1. Install package into target agent's venv or system
# Option A: Python venv (recommended)
python3 -m venv ~/.venvs/second-brain
source ~/.venvs/second-brain/bin/activate
pip install second-brain[server]

# Option B: into existing agent venv (Hermes, HeartMuLa, etc.)
source /path/to/agent/venv/bin/activate
pip install second-brain[server]

# 2. Initialize brain directory
second-brain init

# 3. Create agent token
second-brain server token-create --agent <agent-name> --note "deployed on <hostname>"

# 4. Start server (foreground test)
second-brain server serve --host 0.0.0.0 --port 8009

# 5. (Production) Install as systemd user service
cp deploy/systemd/second-brain.service ~/.config/systemd/user/
# Edit User= line if needed, set Environment=SECOND_BRAIN_DIR
systemctl --user daemon-reload
systemctl --user enable --now second-brain.service
systemctl --user status second-brain.service

# 6. Verify health
curl http://localhost:8009/health  # returns {"ok":true}
```

## Systemd User Service

Place service at `~/.config/systemd/user/second-brain.service`.

Enable linger (start at boot without login):
```bash
loginctl enable-linger $USER
```

Then:
```bash
systemctl --user enable second-brain
systemctl --user start second-brain
journalctl --user -u second-brain -f
```

## Reverse Proxy (nginx)

```nginx
server {
    listen 443 ssl;
    server_name brain.primes.xyz;
    location / {
        proxy_pass http://127.0.0.1:8009;
    }
}
```

Server is write-only; no read endpoints exposed.

## Agent Configuration (remote writers)

```bash
export SECOND_BRAIN_SERVER_URL="http://brain-host:8009"
export SECOND_BRAIN_TOKEN="tok_..."
```

Hermes plugin auto-detects these and switches to HTTP mode.

## Monitoring

Health: `GET /health` → `{"ok":true}`

Logs: `journalctl --user -u second-brain -f`

## Security

- Tokens are write-only (`events:write` scope)
- Bind to localhost unless behind reverse proxy
- Rotate tokens: `second-brain server token-revoke <id>` then recreate
- Back up `brain.key` separately

## Troubleshooting

| Symptom | Check |
|---------|-------|
| 502 from reverse proxy | Is server running? `systemctl --user status second-brain` |
| 401 from POST | Token correct? `second-brain server token-list` |
| DB locked | WAL mode (default); avoid concurrent writes from multiple sources |

