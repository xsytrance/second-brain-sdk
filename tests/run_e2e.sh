#!/usr/bin/env bash
set -euo pipefail
cd "/home/xsyprime/second-brain-sdk"
export GIT_TERMINAL_PROMPT=0
python -m tests.e2e_verify
