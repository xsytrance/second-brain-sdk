# Installation Guide

This guide covers installing Second Brain across different environments and common platform-specific gotchas.

---

## Quick Install (any OS)

```bash
pip install second-brain
pip install 'second-brain[server]'   # optional: for FastAPI server
```

Initialize:
```bash
second-brain init
```

That's it.

---

## Platform Notes

### Ubuntu / Debian (system Python)

Modern Ubuntu (23.04+) marks system Python as externally-managed. Avoid `pip install` against system Python. Choose ONE:

#### Option A: Use a virtual environment (recommended)
```bash
python3 -m venv ~/.venvs/second-brain
source ~/.venvs/second-brain/bin/activate
pip install second-brain
second-brain init
```

#### Option B: Use `--break-system-packages` (not recommended, may break system tools)
```bash
pip install --break-system-packages second-brain
```

### macOS

Use Homebrew Python or pyenv:
```bash
brew install python
pip3 install second-brain
second-brain init
```

### Windows

Use the Microsoft Store Python or Anaconda:
```powershell
pip install second-brain
second-brain init
```

---

## Hermes Agent (PRIME / VPS / VENUS)

Hermes already manages a virtual environment at `~/.hermes/hermes-agent/venv`.

Install directly into it:

```bash
source ~/.hermes/hermes-agent/venv/bin/activate
pip install second-brain
pip install 'second-brain[server]'   # if running server mode
second-brain init
```

Verify:
```bash
second-brain events --limit 5  # should show empty list, no errors
```

The Hermes plugin is loaded from `~/.hermes/plugins/second_brain/` (if you've copied it).

---

## Cloning from GitHub

The repo is public: https://github.com/xsytrance/second-brain-sdk

If you encounter SSH issues (host key mismatch, missing askpass), use HTTPS with a Personal Access Token (PAT):

```bash
git clone https://<TOKEN>@github.com/xsytrance/second-brain-sdk.git
```

Or configure SSH properly:

```bash
ssh-keygen -t ed25519 -C "you@example.com"   # if you don't have a key
ssh-add ~/.ssh/id_ed25519
ssh-keyscan github.com >> ~/.ssh/known_hosts
```

---

## Upgrading

```bash
pip install --upgrade second-brain
```

### Schema migrations

Between minor versions, the schema may change. The SDK auto-runs `init_db()` on first use, but won't alter existing tables. If a new version requires a schema change:

```bash
second-brain migrate   # (future command; currently re-init needed)
```

Currently, if you see schema errors, back up your `brain.db`, delete it, and re-run `second-brain init`. Events can be replayed if you have a backup; credentials cannot be recovered without `brain.key`.

---

## Uninstall

```bash
pip uninstall second-brain
# Optionally remove data
rm -rf ~/.second-brain
```

**Warning**: Removing the brain directory deletes all events and encrypted credentials. Back up first with `second-brain export` (future feature).

