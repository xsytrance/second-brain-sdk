from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

from cryptography.fernet import Fernet, InvalidToken

from .crypto.keys import ensure_key_file
from .storage.sqlite_store import SQLiteStore


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_brain_dir() -> Path:
    env = os.environ.get("SECOND_BRAIN_DIR")
    if env:
        return Path(env).expanduser()
    return Path.home() / ".second-brain"


@dataclass
class Brain:
    """High-level interface over the SQLite store.

    This is the new core for the generalized standalone package.

    Encryption policy (locked):
    - Events are stored plaintext.
    - Credentials are stored encrypted (Fernet).
    """

    brain_dir: Path

    @classmethod
    def default(cls) -> "Brain":
        return cls(default_brain_dir())

    @property
    def db_path(self) -> Path:
        return self.brain_dir / "brain.db"

    @property
    def key_path(self) -> Path:
        return self.brain_dir / "brain.key"

    def _store(self) -> SQLiteStore:
        return SQLiteStore(self.db_path)

    def init(self) -> None:
        self.brain_dir.mkdir(parents=True, exist_ok=True)
        self._store().init_db()
        ensure_key_file(self.key_path)

    # ---- events ----
    def log_event(
        self,
        *,
        type: str,
        title: str,
        details: Optional[str] = None,
        project: Optional[str] = None,
        outcome: str = "passed",
        tags: Optional[list[str]] = None,
        session_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        meta: Optional[dict[str, Any]] = None,
    ) -> str:
        self.init()
        eid = f"evt_{uuid4().hex[:12]}"
        row = {
            "id": eid,
            "ts": _now(),
            "type": type,
            "title": title,
            "details": details,
            "project": project,
            "outcome": outcome,
            "tags": tags or [],
            "session_id": session_id,
            "agent_id": agent_id,
            "meta": meta or {},
        }
        self._store().insert_event(row)
        return eid

    def list_events(
        self,
        *,
        project: Optional[str] = None,
        agent_id: Optional[str] = None,
        failed_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        self.init()
        return self._store().list_events(
            project=project,
            agent_id=agent_id,
            failed_only=failed_only,
            limit=limit,
            offset=offset,
        )

    # ---- credentials ----
    def _fernet(self) -> Fernet:
        self.init()
        key = ensure_key_file(self.key_path)
        return Fernet(key)

    def store_credential(
        self,
        *,
        service: str,
        kind: str,
        context: str,
        value: str,
        expires_at: Optional[str] = None,
        rotation_note: Optional[str] = None,
    ) -> str:
        from .models.credential import CredentialRecord

        self.init()
        f = self._fernet()
        cid = f"cred_{uuid4().hex[:12]}"
        enc = f.encrypt(value.encode()).decode()
        rec = CredentialRecord(
            id=cid,
            created_at=_now(),
            service=service,
            kind=kind,
            context=context,
            value_enc=enc,
            last_used=None,
            expires_at=expires_at,
            rotation_note=rotation_note,
        )
        self._store().insert_credential(rec.model_dump())
        return cid

    def get_credential(self, cred_id: str) -> Optional[str]:
        self.init()
        row = self._store().get_credential_row(cred_id)
        if not row:
            return None
        f = self._fernet()
        try:
            value = f.decrypt(row["value_enc"].encode()).decode()
        except InvalidToken:
            return None
        self._store().touch_credential_last_used(cred_id, _now())
        return value

    def list_credentials(
        self, *, service: Optional[str] = None
    ) -> list[dict[str, Any]]:
        self.init()
        rows = self._store().list_credentials(service=service)
        # never return decrypted values
        for r in rows:
            r.pop("value_enc", None)
        return rows
