#!/usr/bin/env bash
# Second Brain repo-local bootstrap for agents.
# Usage: ./scripts/install.sh /path/to/second-brain-sdk [--server] [--token-for AGENT] [--brain-dir PATH]

set -euo pipefail

if [[ $# -lt 1 ]]; then
  cat >&2 <<'USAGE'
Usage: scripts/install.sh /path/to/second-brain-sdk [second-brain install options]

Examples:
  scripts/install.sh "$PWD"
  scripts/install.sh /opt/second-brain-sdk --server
  scripts/install.sh ~/second-brain-sdk --server --token-for "$(hostname)"
USAGE
  exit 2
fi

REPO_DIR="$1"
shift || true

if [[ ! -d "$REPO_DIR" ]]; then
  echo "[FAIL] Repo path does not exist: $REPO_DIR" >&2
  exit 1
fi

REPO_DIR="$(cd "$REPO_DIR" && pwd)"
if [[ ! -f "$REPO_DIR/pyproject.toml" || ! -d "$REPO_DIR/second_brain" ]]; then
  echo "[FAIL] Not a Second Brain repo: $REPO_DIR" >&2
  echo "       Expected pyproject.toml and second_brain/" >&2
  exit 1
fi

VENV_PATH="${SECOND_BRAIN_VENV:-$HOME/.venvs/second-brain}"
PYTHON_BIN="${PYTHON:-python3}"

echo "=== Second Brain Repo Installer ==="
echo "Repo : $REPO_DIR"
echo "Venv : $VENV_PATH"

if [[ ! -x "$VENV_PATH/bin/python" ]]; then
  mkdir -p "$(dirname "$VENV_PATH")"
  "$PYTHON_BIN" -m venv "$VENV_PATH"
fi

"$VENV_PATH/bin/python" -m pip install --upgrade pip
"$VENV_PATH/bin/python" -m pip install --upgrade -e "$REPO_DIR[server]"

mkdir -p "$HOME/.local/bin" "$HOME/bin"
ln -sf "$VENV_PATH/bin/second-brain" "$HOME/.local/bin/second-brain"
ln -sf "$VENV_PATH/bin/second-brain" "$HOME/bin/second-brain"

echo "=== Delegating to second-brain install ==="
"$VENV_PATH/bin/second-brain" install "$REPO_DIR" "$@"

echo ""
echo "✓ Installation complete"
echo "CLI: $VENV_PATH/bin/second-brain"
echo "Also linked: $HOME/.local/bin/second-brain and $HOME/bin/second-brain"
