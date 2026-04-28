from __future__ import annotations

from pathlib import Path

from cryptography.fernet import Fernet


def ensure_key_file(key_path: Path) -> bytes:
    """Create a new Fernet key file if missing, otherwise read it."""
    key_path.parent.mkdir(parents=True, exist_ok=True)
    if key_path.exists():
        return key_path.read_bytes()
    key = Fernet.generate_key()
    key_path.write_bytes(key)
    return key
