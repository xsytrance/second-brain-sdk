#!/bin/bash
set -euo pipefail
VENV_PATH="${VENV_PATH:-$HOME/.venvs/second-brain}"
BRAIN_DIR="${BRAIN_DIR:-$HOME/.second-brain}"
echo "=== Second Brain Agent Bootstrap ==="
if ! command -v python3 &>/dev/null; then echo "ERROR: python3 not found"; exit 1; fi
if [ ! -d "$VENV_PATH" ]; then python3 -m venv "$VENV_PATH"; fi
source "$VENV_PATH/bin/activate"
if [ ! -d "$HOME/second-brain-sdk" ]; then git clone https://github.com/xsytrance/second-brain-sdk.git "$HOME/second-brain-sdk"; fi
cd "$HOME/second-brain-sdk"
pip install -e .[server]
export SECOND_BRAIN_DIR="$BRAIN_DIR"
second-brain init
second-brain status
echo "Installation complete."
