from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


@dataclass
class SQLiteStore:
    """Low-level SQLite storage.

    This store is intentionally dumb: it does not do encryption itself.
    It provides transactional reads/writes and sets safe pragmas.
    """

    db_path: Path

    def connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        self._apply_pragmas(conn)
        return conn

    def _apply_pragmas(self, conn: sqlite3.Connection) -> None:
        conn.execute("PRAGMA foreign_keys = ON")
        # WAL improves concurrency for multi-agent workloads.
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")

    def init_db(self) -> None:
        schema_path = Path(__file__).with_name("schema.sql")
        ddl = _read_text(schema_path)
        with self.connect() as conn:
            conn.executescript(ddl)
            # set schema version if missing
            conn.execute(
                "INSERT OR IGNORE INTO meta(key, value) VALUES('schema_version', '2')"
            )
            # If upgrading an older DB, bump version.
            conn.execute(
                "UPDATE meta SET value = '2' WHERE key = 'schema_version' AND CAST(value AS INTEGER) < 2"
            )
            conn.commit()

    # --- events ---
    def insert_event(self, row: dict[str, Any]) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO events(id, ts, type, title, details, project, outcome, tags_json, session_id, agent_id, meta_json)
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["id"],
                    row["ts"],
                    row["type"],
                    row["title"],
                    row.get("details"),
                    row.get("project"),
                    row.get("outcome", "passed"),
                    json.dumps(row.get("tags", []), ensure_ascii=False),
                    row.get("session_id"),
                    row.get("agent_id"),
                    json.dumps(row.get("meta", {}), ensure_ascii=False),
                ),
            )
            conn.commit()

    def list_events(
        self,
        *,
        project: Optional[str] = None,
        agent_id: Optional[str] = None,
        outcome: Optional[str] = None,
        failed_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []

        if project:
            clauses.append("project = ?")
            params.append(project)
        if agent_id:
            clauses.append("agent_id = ?")
            params.append(agent_id)
        if outcome:
            clauses.append("outcome = ?")
            params.append(outcome)
        if failed_only:
            clauses.append("outcome = 'failed'")

        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        sql = f"SELECT * FROM events {where} ORDER BY ts DESC LIMIT ? OFFSET ?"
        params.extend([int(limit), int(offset)])

        with self.connect() as conn:
            rows = conn.execute(sql, params).fetchall()

        out: list[dict[str, Any]] = []
        for r in rows:
            d = dict(r)
            d["tags"] = json.loads(d.get("tags_json") or "[]")
            d["meta"] = json.loads(d.get("meta_json") or "{}")
            d.pop("tags_json", None)
            d.pop("meta_json", None)
            out.append(d)
        return out

    # --- credentials ---
    def insert_credential(self, row: dict[str, Any]) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO credentials(id, created_at, service, kind, context, value_enc, last_used, expires_at, rotation_note)
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["id"],
                    row["created_at"],
                    row["service"],
                    row["kind"],
                    row["context"],
                    row["value_enc"],
                    row.get("last_used"),
                    row.get("expires_at"),
                    row.get("rotation_note"),
                ),
            )
            conn.commit()

    def list_credentials(self, *, service: Optional[str] = None) -> list[dict[str, Any]]:
        where = ""
        params: list[Any] = []
        if service:
            where = "WHERE service = ?"
            params.append(service)
        with self.connect() as conn:
            rows = conn.execute(f"SELECT * FROM credentials {where} ORDER BY created_at DESC", params).fetchall()
        return [dict(r) for r in rows]

    def get_credential_row(self, cred_id: str) -> Optional[dict[str, Any]]:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM credentials WHERE id = ?", (cred_id,)).fetchone()
        return dict(row) if row else None

    def touch_credential_last_used(self, cred_id: str, ts: str) -> None:
        with self.connect() as conn:
            conn.execute("UPDATE credentials SET last_used = ? WHERE id = ?", (ts, cred_id))
            conn.commit()

    # --- api tokens (server) ---
    def create_api_token(self, *, token_id: str, created_at: str, agent_id: str, raw_token: str, scopes: list[str], note: Optional[str] = None) -> None:
        token_hash = _sha256_hex(raw_token)
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO api_tokens(id, created_at, agent_id, token_hash, scopes_json, note)
                VALUES(?, ?, ?, ?, ?, ?)
                """,
                (token_id, created_at, agent_id, token_hash, json.dumps(scopes, ensure_ascii=False), note),
            )
            conn.commit()

    def list_api_tokens(self, *, agent_id: Optional[str] = None) -> list[dict[str, Any]]:
        where = ""
        params: list[Any] = []
        if agent_id:
            where = "WHERE agent_id = ?"
            params.append(agent_id)
        with self.connect() as conn:
            rows = conn.execute(f"SELECT * FROM api_tokens {where} ORDER BY created_at DESC", params).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["scopes"] = json.loads(d.get("scopes_json") or "[]")
            d.pop("scopes_json", None)
            out.append(d)
        return out

    def revoke_api_token(self, token_id: str, ts: str) -> None:
        with self.connect() as conn:
            conn.execute("UPDATE api_tokens SET revoked_at = ? WHERE id = ?", (ts, token_id))
            conn.commit()

    def auth_token_lookup(self, raw_token: str) -> Optional[dict[str, Any]]:
        token_hash = _sha256_hex(raw_token)
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM api_tokens WHERE token_hash = ? AND revoked_at IS NULL",
                (token_hash,),
            ).fetchone()
        if not row:
            return None
        d = dict(row)
        d["scopes"] = json.loads(d.get("scopes_json") or "[]")
        d.pop("scopes_json", None)
        return d

    def touch_token_last_used(self, token_id: str, ts: str) -> None:
        with self.connect() as conn:
            conn.execute("UPDATE api_tokens SET last_used = ? WHERE id = ?", (ts, token_id))
            conn.commit()
