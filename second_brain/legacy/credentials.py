"""Credential management with encryption."""

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from cryptography.fernet import Fernet

from .core import Credential, Vault


class CredentialManager:
    """Manages credentials: add, retrieve, rotate, list."""

    def __init__(self, vault: Vault):
        self.vault = vault

    def store(
        self,
        service: str,
        kind: str,
        context: str,
        value: str,
        expires_at: Optional[str] = None,
        rotation_note: Optional[str] = None,
    ) -> Credential:
        """Encrypt and store a credential."""
        return self.vault.add_credential(
            service=service,
            kind=kind,
            context=context,
            plaintext_value=value,
            expires_at=expires_at,
            rotation_note=rotation_note or "Rotate every 60 days",
        )

    def retrieve(self, cred_id: str) -> Optional[str]:
        """Decrypt and return a credential value."""
        return self.vault.get_credential(cred_id)

    def find_by_service(self, service: str) -> List[Dict[str, Any]]:
        """Find all credentials for a service (metadata only, no values)."""
        return self.vault.find_credentials(service)

    def find_recent(self, service: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Get recent credentials for a service, sorted by last_used desc."""
        creds = self.find_by_service(service)
        return sorted(
            creds,
            key=lambda c: c.get("last_used", "") or c.get("created_at", ""),
            reverse=True,
        )[:limit]

    def mark_used(self, cred_id: str) -> None:
        """Update last_used timestamp for a credential."""
        vault_data = self.vault._data
        for cred in vault_data["credentials"]:
            if cred["id"] == cred_id:
                cred["last_used"] = datetime.now(timezone.utc).isoformat()
                self.vault._encrypt_and_save()
                break

    def rotate(
        self, cred_id: str, new_value: str, reason: str = "Scheduled rotation"
    ) -> Credential:
        """Replace an existing credential with a new value, logging rotation."""
        # Decrypt old one to get metadata
        old_meta = None
        for cred in self.vault._data["credentials"]:
            if cred["id"] == cred_id:
                old_meta = cred
                break

        if not old_meta:
            raise ValueError(f"Credential {cred_id} not found")

        # Delete old (we'll create new)
        self.vault._data["credentials"] = [
            c for c in self.vault._data["credentials"] if c["id"] != cred_id
        ]

        # Create new with rotation note
        rotation_note = f"Rotated {datetime.now(timezone.utc).isoformat()}: {reason}. Previous ID: {cred_id}"
        new_cred = self.store(
            service=old_meta["service"],
            kind=old_meta["kind"],
            context=old_meta["context"],
            value=new_value,
            expires_at=old_meta.get("expires_at"),
            rotation_note=rotation_note,
        )

        # Log rotation event
        self.vault.log_event(
            event_type="credential_rotated",
            title=f"Rotated {old_meta['service']} {old_meta['kind']}",
            details=f"Old ID: {cred_id} → New ID: {new_cred.id}. Reason: {reason}",
            tags=["security", "rotation"],
        )

        return new_cred
