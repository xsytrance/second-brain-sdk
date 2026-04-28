#!/bin/bash
# Second Brain quick install for VG Clan agents
# Usage: ./install.sh [--venv PATH] [--brain-dir PATH]

set -e

VENV_PATH="${1:-$HOME/.venv/second-brain}"
BRAIN_DIR="${2:-$HOME/.second-brain}"

echo "=== Second Brain Agent Installer ==="
echo "Venv: $VENV_PATH"
echo "Brain dir: $BRAIN_DIR"

# Create venv
python3 -m venv "$VENV_PATH"
source "$VENV_PATH/bin/activate"

# Install
pip install --upgrade pip
pip install second-brain[server]

# Init brain
export SECOND_BRAIN_DIR="$BRAIN_DIR"
second-brain init

# Create agent token (optional, for server mode)
# second-brain server token-create --agent $(hostname) --note "auto-installed"

echo "✓ Installation complete"
echo ""
echo "Next steps:"
echo "1. Add to your agent's startup:"
echo "   source $VENV_PATH/bin/activate"
echo "   export SECOND_BRAIN_DIR=$BRAIN_DIR"
echo ""
echo "2. (Optional) Enable server mode to accept remote writes:"
echo "   second-brain server token-create --agent $(hostname)"
echo "   second-brain server serve --host 127.0.0.1 --port 8009 &"
echo ""
echo "3. Test:"
echo "   second-brain status"
