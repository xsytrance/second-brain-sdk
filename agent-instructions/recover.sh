#!/bin/bash
set -e
if [ $# -ne 2 ]; then echo "Usage: $0 <backup_brain.db> <backup_brain.key>"; exit 1; fi
BACKUP_DB="$1"; BACKUP_KEY="$2"
TARGET="${SECOND_BRAIN_DIR:-$HOME/.second-brain}"
echo "Recovering from:"; echo "  DB: $BACKUP_DB"; echo "  Key: $BACKUP_KEY"; echo "  To: $TARGET"
systemctl --user stop second-brain 2>/dev/null || true
[ -d "$TARGET" ] && cp -r "$TARGET" "${TARGET}.backup.$(date +%Y%m%d_%H%M%S)"
mkdir -p "$TARGET"; cp "$BACKUP_DB" "$TARGET/brain.db"; cp "$BACKUP_KEY" "$TARGET/brain.key"
chmod 600 "$TARGET/brain.key"; chmod 700 "$TARGET"
echo "Recovery complete. second-brain status"
