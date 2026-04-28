"""Core vault management with Fernet encryption."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from cryptography.fernet import Fernet, InvalidToken


class Event:
    """Represents a single logged event in the Second Brain."""

    def __init__(
        self,
        event_type: str,
        title: str,
        details: Optional[str] = None,
        project: Optional[str] = None,
        outcome: str = "passed",
        error: Optional[str] = None,
        files_changed: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        session_id: Optional[str] = None,
        next_steps: Optional[List[str]] = None,
    ):
        self.id = f"evt_{uuid4().hex[:12]}"
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.type = event_type
        self.title = title
        self.details = details
        self.project = project
        # Infer outcome from type if not explicitly provided
        if outcome == "passed" and event_type.endswith("_failed"):
            self.outcome = "failed"
        elif outcome == "passed" and event_type.endswith("_completed"):
            self.outcome = "passed"
        else:
            self.outcome = outcome  # "passed", "failed", "skipped", "cancelled"
        self.error = error
        self.files_changed = files_changed or []
        self.tags = tags or []
        self.session_id = session_id
        self.next_steps = next_steps or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "type": self.type,
            "title": self.title,
            "details": self.details,
            "project": self.project,
            "outcome": self.outcome,
            "error": self.error,
            "files_changed": self.files_changed,
            "tags": self.tags,
            "session_id": self.session_id,
            "next_steps": self.next_steps,
        }


class Credential:
    """Represents an encrypted credential record."""

    def __init__(
        self,
        service: str,
        kind: str,
        context: str,
        encrypted_value: str,
        created_at: Optional[str] = None,
        expires_at: Optional[str] = None,
        rotation_note: Optional[str] = None,
    ):
        self.id = f"cred_{uuid4().hex[:12]}"
        self.created_at = created_at or datetime.now(timezone.utc).isoformat()
        self.service = service
        self.kind = kind
        self.context = context
        self.encrypted_value = encrypted_value  # Already encrypted
        self.expires_at = expires_at
        self.rotation_note = rotation_note
        self.last_used: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "created_at": self.created_at,
            "service": self.service,
            "kind": self.kind,
            "context": self.context,
            "encrypted_value": self.encrypted_value,
            "expires_at": self.expires_at,
            "rotation_note": self.rotation_note,
            "last_used": self.last_used,
        }


class Vault:
    """Encrypted vault for all Second Brain data."""

    def __init__(self, path: str, key_path: Optional[str] = None):
        self.path = Path(path)
        self.key_path = (
            Path(key_path) if key_path else self.path.parent / "decryption_key.key"
        )
        self._fernet: Optional[Fernet] = None
        self._data: Dict[str, Any] = {
            "version": "1.0",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "events": [],
            "credentials": [],
            "skills_created": [],
            "identity": {},
        }
        self._load_or_init()

    def _load_or_init(self) -> None:
        """Load existing vault or initialize a new one."""
        if self.path.exists():
            self._decrypt_and_load()
        else:
            self._encrypt_and_save()

    def _get_fernet(self) -> Fernet:
        """Get or create Fernet cipher."""
        if self._fernet:
            return self._fernet

        if self.key_path.exists():
            with open(self.key_path, "rb") as f:
                key = f.read()
        else:
            key = Fernet.generate_key()
            with open(self.key_path, "wb") as f:
                f.write(key)
            print(f"⚠  Generated new encryption key at {self.key_path}")
            print("   BACK IT UP SEPARATELY — vault is unrecoverable without it!")

        self._fernet = Fernet(key)
        return self._fernet

    def _decrypt_and_load(self) -> None:
        """Decrypt and parse vault file."""
        fernet = self._get_fernet()
        with open(self.path, "rb") as f:
            encrypted = f.read()
        try:
            decrypted = fernet.decrypt(encrypted)
            self._data = json.loads(decrypted)
        except InvalidToken:
            raise ValueError("Cannot decrypt vault — invalid or missing key")

    def _encrypt_and_save(self) -> None:
        """Encrypt and write vault to disk."""
        fernet = self._get_fernet()
        json_str = json.dumps(self._data, indent=2, ensure_ascii=False)
        encrypted = fernet.encrypt(json_str.encode())
        with open(self.path, "wb") as f:
            f.write(encrypted)

    # ── Events ──────────────────────────────────────────────────────────────

    def log_event(
        self,
        event_type: str,
        title: str,
        details: Optional[str] = None,
        project: Optional[str] = None,
        outcome: str = "passed",
        error: Optional[str] = None,
        files_changed: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        session_id: Optional[str] = None,
        next_steps: Optional[List[str]] = None,
    ) -> Event:
        """Log an event to the vault."""
        event = Event(
            event_type=event_type,
            title=title,
            details=details,
            project=project,
            outcome=outcome,
            error=error,
            files_changed=files_changed,
            tags=tags,
            session_id=session_id,
            next_steps=next_steps,
        )
        self._data["events"].append(event.to_dict())
        self._encrypt_and_save()
        return event

    def get_events(
        self,
        project: Optional[str] = None,
        tags: Optional[List[str]] = None,
        outcome: Optional[str] = None,
        since: Optional[str] = None,
        until: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Query events with filters."""
        events = self._data["events"]
        if project:
            events = [e for e in events if e.get("project") == project]
        if tags:
            events = [e for e in events if any(t in e.get("tags", []) for t in tags)]
        if outcome:
            events = [e for e in events if e.get("outcome") == outcome]
        if since:
            events = [e for e in events if e.get("timestamp", "") >= since]
        if until:
            events = [e for e in events if e.get("timestamp", "") <= until]
        return sorted(events, key=lambda e: e["timestamp"], reverse=True)[:limit]

    # ── Credentials ────────────────────────────────────────────────────────

    def add_credential(
        self,
        service: str,
        kind: str,
        context: str,
        plaintext_value: str,
        expires_at: Optional[str] = None,
        rotation_note: Optional[str] = None,
    ) -> Credential:
        """Encrypt and store a credential."""
        fernet = self._get_fernet()
        encrypted = fernet.encrypt(plaintext_value.encode()).decode()
        cred = Credential(
            service=service,
            kind=kind,
            context=context,
            encrypted_value=encrypted,
            expires_at=expires_at,
            rotation_note=rotation_note,
        )
        self._data["credentials"].append(cred.to_dict())
        self._encrypt_and_save()
        return cred

    def get_credential(self, cred_id: str) -> Optional[str]:
        """Decrypt and return a credential value by ID."""
        for cred_dict in self._data["credentials"]:
            if cred_dict["id"] == cred_id:
                fernet = self._get_fernet()
                try:
                    return fernet.decrypt(
                        cred_dict["encrypted_value"].encode()
                    ).decode()
                except InvalidToken:
                    return None
        return None

    def find_credentials(self, service: Optional[str] = None) -> List[Dict[str, Any]]:
        """List credential metadata (not decrypted values)."""
        creds = self._data["credentials"]
        if service:
            creds = [c for c in creds if c.get("service") == service]
        return creds

    # ── Skills ─────────────────────────────────────────────────────────────

    def register_skill(
        self,
        name: str,
        category: str,
        path: str,
        purpose: str,
        status: str = "active",
    ) -> Dict[str, Any]:
        """Track a created skill."""
        skill = {
            "name": name,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "category": category,
            "path": path,
            "purpose": purpose,
            "status": status,
        }
        self._data["skills_created"].append(skill)
        self._encrypt_and_save()
        return skill

    def get_skills(self) -> List[Dict[str, Any]]:
        """List all registered skills."""
        return self._data["skills_created"]

    # ── Identity ────────────────────────────────────────────────────────────

    def set_identity(self, agent: Dict[str, Any], user: Dict[str, Any]) -> None:
        """Store agent and user identity (unencrypted in vault)."""
        self._data["identity"] = {"agent": agent, "user": user}
        self._encrypt_and_save()

    def get_identity(self) -> Dict[str, Any]:
        """Retrieve stored identity."""
        return self._data.get("identity", {})

    # ── Export / Summary ───────────────────────────────────────────────────

    def export_session_summary(
        self,
        session_id: str,
        output_path: Optional[str] = None,
    ) -> str:
        """Generate a Markdown summary of a session's events."""
        events = [e for e in self._data["events"] if e.get("session_id") == session_id]
        if not events:
            return f"# Session {session_id}\n\nNo events found."

        first = min(events, key=lambda e: e["timestamp"])
        last = max(events, key=lambda e: e["timestamp"])

        lines = [
            f"# Session {session_id}",
            f"\n**Start:** {first['timestamp']}",
            f"**End:** {last['timestamp']}",
            f"**Events logged:** {len(events)}",
            f"\n---\n",
        ]

        for evt in sorted(events, key=lambda e: e["timestamp"]):
            icon = {"passed": "✅", "failed": "❌", "skipped": "⏭️"}.get(
                evt["outcome"], "•"
            )
            lines.append(f"{icon} **{evt['title']}** — {evt['outcome']}")
            if evt.get("error"):
                lines.append(f"   > Error: {evt['error']}")
            if evt.get("files_changed"):
                for f in evt["files_changed"]:
                    lines.append(f"   📄 {f}")
            if evt.get("next_steps"):
                lines.append("   Next steps:")
                for step in evt["next_steps"]:
                    lines.append(f"     - {step}")
            lines.append("")

        summary = "\n".join(lines)
        if output_path:
            with open(output_path, "w") as f:
                f.write(summary)
        return summary

    def get_statistics(self) -> Dict[str, Any]:
        """Return basic vault statistics."""
        evts = self._data["events"]
        outcomes = [e["outcome"] for e in evts]
        return {
            "total_events": len(evts),
            "passed": outcomes.count("passed"),
            "failed": outcomes.count("failed"),
            "skipped": outcomes.count("skipped"),
            "total_credentials": len(self._data["credentials"]),
            "skills_tracked": len(self._data["skills_created"]),
            "vault_created": self._data["created_at"],
        }
