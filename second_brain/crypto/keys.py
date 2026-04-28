from __future__ import annotations

from pathlib import Path
import os

from cryptography.fernet import Fernet


def ensure_key_file(key_path: Path) -> bytes:
    """Create a new Fernet key file if missing, otherwise read it."""
    key_path.parent.mkdir(parents=True, exist_ok=True)
    if key_path.exists():
        return key_path.read_bytes()
    key = Fernet.generate_key()
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    fd = os.open(key_path, flags, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(key)
    return key
