# Second Brain SDK — File Index

## 🗂️ Repository Structure

```
second-brain-sdk/
├── README.md                    # Main project documentation
├── LICENSE                      # MIT License
├── pyproject.toml               # Build configuration (setuptools)
├── requirements.txt             # Runtime dependencies
├── requirements-dev.txt         # Dev dependencies
├── .gitignore                   # Git ignore rules
├── .github/
│   └── workflows/
│       └── ci.yml               # GitHub Actions CI (test, lint, build)
├── second_brain/
│   ├── __init__.py              # Package exports
│   ├── core.py                  # Vault, Event, Credential classes
│   ├── session.py               # Session tracking + task context manager
│   ├── query.py                 # Fluent query builder for events
│   ├── credentials.py           # CredentialManager (store/rotate/retrieve)
│   └── cli.py                   # Command-line interface (click + rich)
├── examples/
│   ├── __init__.py
│   ├── quickstart.py            # Minimal "hello world" example
│   └── hermes_integration.py    # Full Hermes agent integration pattern
├── tests/
│   ├── __init__.py
│   └── test_sdk.py              # Unit tests for Vault, Session, Credentials, Query
├── docs/
│   └── USAGE.md                 # Comprehensive usage guide
└── scripts/
    └── create_project.py        # SDK scaffolding script (future)
```

---

## 📦 Module Reference

### `core.py` — Vault, Event, Credential

**Classes:**
- `Event` — dataclass for a single log entry
- `Credential` — dataclass for encrypted credential metadata
- `Vault` — main encrypted store

Key methods:
```python
Vault.log_event(type, title, ...) → Event
Vault.get_events(project=..., tags=..., limit=...) → list
Vault.add_credential(service, kind, context, value) → Credential
Vault.get_credential(cred_id) → str | None
Vault.register_skill(name, category, path, purpose) → dict
Vault.set_identity(agent, user) → None
Vault.export_session_summary(session_id) → str
Vault.get_statistics() → dict
```

### `session.py` — Session

**Class:**
- `Session` — groups events into a conversation/work session

Key methods:
```python
Session(vault, project, session_id=None) → Session
Session.log(type, title, ...) → Event
Session.task(title, ...) → context manager (auto-logs start/completion/failure)
Session.decision(title, details, reasoning, alternatives) → Event
Session.milestone(title, details) → Event
Session.end(summary) → str (markdown)
Session.save_summary(output_dir) → str (filepath)
```

### `query.py` — Filter & Search

**Class:**
- `Query` — fluent query builder

Usage:
```python
Query(vault).project("myapp").tag("api").passed().limit(10).all()
Query(vault).failed().since("2026-04-27").all()
Query.recent_failures(vault, hours=24)
Query.by_project(vault, "nook-polish")
Query.milestone_timeline(vault)
```

### `credentials.py` — Credential Manager

**Class:**
- `CredentialManager` — high-level API for encrypted secrets

Methods:
```python
CredentialManager(vault)
  .store(service, kind, context, value, ...) → Credential
  .retrieve(cred_id) → str
  .find_by_service(service) → list[metadata]
  .mark_used(cred_id) → None
  .rotate(cred_id, new_value, reason) → new_credential
```

### `cli.py` — Command-Line Interface

Commands:
```bash
second-brain init
second-brain log <type> <title> [options]
second-brain events [--project X] [--tag Y] [--failed]
second-brain stats
second-brain credential add|list|get|rotate
second-brain summary
second-brain export
second-brain info
```

---

## 🔐 File Format Details

### `vault.json.enc` (encrypted)

Fernet-encrypted JSON blob. Full structure:

```json
{
  "version": "1.0",
  "created_at": "ISO8601",
  "events": [ { ... Event dict ... } ],
  "credentials": [ { ... Credential dict (encrypted_value field) ... } ],
  "skills_created": [ { name, category, path, purpose, status, created_at } ],
  "identity": { "agent": {...}, "user": {...} }
}
```

### `decryption_key.key`

32-byte URL-safe base64 Fernet key. Example:
```
gAAAAABmY2R4Z... (44 chars)
```

**Back this up!** Without it, the vault is unrecoverable.

### `config.yaml`

```yaml
retention_days: 365
auto_summarize: true
export_quarterly: true
key_backup_reminder: "Monthly: backup decryption_key.key to external storage"
```

### `identity.json`

Quick-reference identity (not encrypted):

```json
{
  "agent": { "name": "Hermes", ... },
  "user": { "name": "Snooky Gomez", "alias": "Snow", ... }
}
```

### `sessions/*.md`

Markdown session summaries (human-readable timeline).

### `index.md`

Top-level index linking to sessions — Markdown file for easy browsing.

---

## 🚀 Deployment to PyPI

1. Bump version in `pyproject.toml` and `__init__.py`
2. Build: `python -m build`
3. Check: `twine check dist/*`
4. Upload: `twine upload dist/*` (requires PyPI token)

GitHub Actions will auto-publish on tag push when enabled.

---

## 🤝 Contributing

- Add tests in `tests/`
- Format with `black` and `isort`
- Type-check with `mypy`
- Update `docs/` with new usage patterns
- Keep `CHANGELOG.md` updated (create one if publishing)

---

**Index generated from source tree.** For full docs, see README.md and docs/USAGE.md.
