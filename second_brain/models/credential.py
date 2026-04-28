from __future__ import annotations

from pydantic import BaseModel


class CredentialRecord(BaseModel):
    id: str
    created_at: str
    service: str
    kind: str
    context: str
    value_enc: str
    last_used: str | None = None
    expires_at: str | None = None
    rotation_note: str | None = None
