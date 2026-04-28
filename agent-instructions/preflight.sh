#!/bin/bash
FAIL=0
check() { if [ "$2" = "true" ]; then echo "[OK] $1"; else echo "[FAIL] $1"; FAIL=1; fi; }
echo "=== Pre-flight ==="
python3 -c "import sys; sys.exit(0 if sys.version_info >= (3,9) else 1)" &>/dev/null && check "Python >= 3.9" true || check "Python >= 3.9" false
python3 -m venv /tmp/.sb_test 2>/dev/null && rm -rf /tmp/.sb_test && check "venv module" true || check "venv module" false
command -v git &>/dev/null && check "git available" true || check "git available" false
if [ -n "${SECOND_BRAIN_SERVER_URL:-}" ]; then
  host=$(echo "$SECOND_BRAIN_SERVER_URL" | sed -E 's|https?://||;s|:[0-9]+.*||')
  ping -c1 -W2 "$host" &>/dev/null && check "Route to $host" true || check "Route to $host" false
fi
free=$(df -m $HOME | awk 'NR==2 {print $4}')
[ "$free" -ge 100 ] && check "Disk space >=100MB (${free}MB)" true || check "Disk space >=100MB (${free}MB)" false
[ -w "$HOME" ] && check "Home writable" true || check "Home writable" false
echo "exit $FAIL
