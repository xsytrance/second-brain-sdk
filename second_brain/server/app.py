from __future__ import annotations

from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

from ..brain import Brain


class EventIn(BaseModel):
    type: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    details: Optional[str] = None
    project: Optional[str] = None
    outcome: str = "passed"
    tags: list[str] = []
    session_id: Optional[str] = None
    meta: dict[str, Any] = {}


def _bearer_token(req: Request) -> str:
    auth = req.headers.get("authorization") or ""
    if not auth.lower().startswith("bearer "):
        return ""
    return auth.split(" ", 1)[1].strip()


def create_app(brain: Brain) -> FastAPI:
    app = FastAPI(title="Second Brain Server", version="0.1.0")

    @app.get("/health")
    def health():
        brain.init()
        return {"ok": True}

    @app.post("/v1/events")
    def write_event(payload: EventIn, request: Request):
        token = _bearer_token(request)
        if not token:
            raise HTTPException(status_code=401, detail="missing bearer token")

        store = brain._store()
        tok = store.auth_token_lookup(token)
        if not tok:
            raise HTTPException(status_code=401, detail="invalid token")

        scopes = set(tok.get("scopes") or [])
        if "events:write" not in scopes:
            raise HTTPException(status_code=403, detail="missing scope events:write")

        agent_id = tok.get("agent_id")
        eid = brain.log_event(
            type=payload.type,
            title=payload.title,
            details=payload.details,
            project=payload.project,
            outcome=payload.outcome,
            tags=payload.tags,
            session_id=payload.session_id,
            agent_id=agent_id,
            meta=payload.meta,
        )
        from datetime import datetime, timezone

        store.touch_token_last_used(tok["id"], datetime.now(timezone.utc).isoformat())
        return {"event_id": eid}

    return app
