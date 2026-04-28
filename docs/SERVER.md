# Second Brain Server (Optional)

Second Brain ships an **optional** HTTP server so other agents can write events **without** getting access to:
- your `brain.db`
- your `brain.key`

Install:
```bash
pip install 'second-brain[server]'
```

## Quick Start

```bash
export SECOND_BRAIN_DIR=~/.second-brain
second-brain init

# Create a write token for an agent (token printed once)
second-brain server token-create --agent agentA --note "remote agent"

# Run server
second-brain server serve --host 0.0.0.0 --port 8009
```

Health check:
```bash
curl http://localhost:8009/health
```

## Writing Events (agent side)

The server is **write-only** in v1 (safer default). Agents can only call `POST /v1/events`.

```bash
curl -X POST http://localhost:8009/v1/events \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "task_started",
    "title": "hello from agent",
    "details": "optional",
    "project": "demo",
    "outcome": "passed",
    "tags": ["srv"],
    "session_id": null,
    "meta": {"build": "123"}
  }'
```

Notes:
- The `agent_id` is inferred from the token (agents don’t supply it).
- If the token is revoked, requests return `401`.

## Token Management

List tokens:
```bash
second-brain server token-list
second-brain server token-list --agent agentA
```

Revoke token:
```bash
second-brain server token-revoke tok_XXXXXXXXXXXX
```

## Security Notes (practical)

- Treat agent tokens like passwords.
- Prefer TLS/HTTPS when exposing the server beyond localhost.
- Consider placing the server behind a reverse proxy (nginx/Caddy/Traefik) with:
  - HTTPS
  - IP allow-listing (if possible)
  - rate limiting

## Reverse Proxy (nginx example)

Example: proxy `https://brain.example.com/` to local server `127.0.0.1:8009`.

```nginx
server {
  listen 443 ssl;
  server_name brain.example.com;

  location / {
    proxy_pass http://127.0.0.1:8009;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
  }
}
```

## Recommended deployment defaults

- Bind to localhost unless you specifically need remote access:
  - `--host 127.0.0.1`
- If remote is required:
  - run behind HTTPS reverse proxy
  - keep tokens scoped to `events:write`
