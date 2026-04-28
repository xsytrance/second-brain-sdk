"""Second Brain CLI (standalone).

This is the public CLI entrypoint for the standalone package.

Current state (as of v0.1.x):
- Core storage is SQLite (Brain).
- Credentials are encrypted at rest (Fernet). Events are plaintext.
- Optional server mode will be added under the [server] extra.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .brain import Brain
from .storage.sqlite_store import SQLiteStore

console = Console()
app = typer.Typer(
    add_completion=False, help="Second Brain — standalone memory for agents"
)


def _brain(brain_dir: Optional[Path]) -> Brain:
    return Brain(brain_dir) if brain_dir else Brain.default()


@app.command()
def init(
    brain_dir: Optional[Path] = typer.Option(
        None, "--brain-dir", envvar="SECOND_BRAIN_DIR"
    ),
):
    """Initialize a brain directory (creates SQLite DB + key file)."""
    b = _brain(brain_dir)
    b.init()
    console.print(f"[green]✓[/green] Second Brain initialized at {b.brain_dir}")
    console.print(f"DB: {b.db_path}")
    console.print(f"Key: {b.key_path}  [yellow](back this up)[/yellow]")


@app.command()
def log(
    event_type: str = typer.Argument(..., help="Event type (e.g. task_started)"),
    title: str = typer.Argument(..., help="Short title"),
    details: Optional[str] = typer.Option(None, "--details", "-d"),
    project: Optional[str] = typer.Option(None, "--project", "-p"),
    outcome: str = typer.Option("passed", "--outcome"),
    tag: List[str] = typer.Option([], "--tag", "-t"),
    session: Optional[str] = typer.Option(None, "--session"),
    agent: Optional[str] = typer.Option(None, "--agent"),
    brain_dir: Optional[Path] = typer.Option(
        None, "--brain-dir", envvar="SECOND_BRAIN_DIR"
    ),
):
    """Log an event to the SQLite brain."""
    b = _brain(brain_dir)
    eid = b.log_event(
        type=event_type,
        title=title,
        details=details,
        project=project,
        outcome=outcome,
        tags=tag,
        session_id=session,
        agent_id=agent,
    )
    console.print(f"[green]✓[/green] Logged event {eid}")


@app.command()
def events(
    project: Optional[str] = typer.Option(None, "--project", "-p"),
    agent: Optional[str] = typer.Option(None, "--agent"),
    failed: bool = typer.Option(False, "--failed"),
    limit: int = typer.Option(20, "--limit", "-l"),
    offset: int = typer.Option(0, "--offset"),
    brain_dir: Optional[Path] = typer.Option(
        None, "--brain-dir", envvar="SECOND_BRAIN_DIR"
    ),
):
    """List events."""
    b = _brain(brain_dir)
    rows = b.list_events(
        project=project, agent_id=agent, failed_only=failed, limit=limit, offset=offset
    )

    table = Table(title=f"Events ({len(rows)})")
    table.add_column("Time", style="cyan", no_wrap=True)
    table.add_column("Agent", style="magenta", no_wrap=True)
    table.add_column("Type", style="magenta")
    table.add_column("Title", style="white")
    table.add_column("Project", style="green")
    table.add_column("Outcome")

    for e in rows:
        table.add_row(
            (e.get("ts", "")[:16]).replace("T", " "),
            (e.get("agent_id") or "")[:14],
            e.get("type", ""),
            (e.get("title", "") or "")[:50],
            (e.get("project", "") or "")[:18],
            e.get("outcome", ""),
        )

    console.print(table)


credential_app = typer.Typer(help="Manage encrypted credentials")
app.add_typer(credential_app, name="credential")

server_app = typer.Typer(help="Server mode (optional)")
app.add_typer(server_app, name="server")


@credential_app.command("add")
def cred_add(
    service: str,
    kind: str,
    context: str,
    value: str = typer.Option(
        ..., prompt=True, hide_input=True, confirmation_prompt=True
    ),
    expires_at: Optional[str] = typer.Option(None, "--expires"),
    rotation_note: Optional[str] = typer.Option(None, "--rotate"),
    brain_dir: Optional[Path] = typer.Option(
        None, "--brain-dir", envvar="SECOND_BRAIN_DIR"
    ),
):
    b = _brain(brain_dir)
    cid = b.store_credential(
        service=service,
        kind=kind,
        context=context,
        value=value,
        expires_at=expires_at,
        rotation_note=rotation_note,
    )
    console.print(f"[green]✓[/green] Stored credential {cid}")


@credential_app.command("list")
def cred_list(
    service: Optional[str] = typer.Option(None, "--service"),
    brain_dir: Optional[Path] = typer.Option(
        None, "--brain-dir", envvar="SECOND_BRAIN_DIR"
    ),
):
    b = _brain(brain_dir)
    rows = b.list_credentials(service=service)

    table = Table(title=f"Credentials ({len(rows)})")
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Service", style="magenta")
    table.add_column("Kind", style="magenta")
    table.add_column("Context", style="white")
    table.add_column("Created", style="cyan", no_wrap=True)
    table.add_column("Last Used", style="cyan", no_wrap=True)

    for r in rows:
        table.add_row(
            r.get("id", ""),
            r.get("service", ""),
            r.get("kind", ""),
            (r.get("context", "") or "")[:40],
            (r.get("created_at", "") or "")[:10],
            (r.get("last_used", "") or "")[:10],
        )

    console.print(table)


@credential_app.command("get")
def cred_get(
    credential_id: str,
    brain_dir: Optional[Path] = typer.Option(
        None, "--brain-dir", envvar="SECOND_BRAIN_DIR"
    ),
):
    b = _brain(brain_dir)
    value = b.get_credential(credential_id)
    if value is None:
        raise typer.Exit(code=1)
    console.print(Panel(value, title=f"🔐 {credential_id}", border_style="green"))


@server_app.command("token-create")
def token_create(
    agent: str = typer.Option(..., "--agent"),
    note: Optional[str] = typer.Option(None, "--note"),
    brain_dir: Optional[Path] = typer.Option(
        None, "--brain-dir", envvar="SECOND_BRAIN_DIR"
    ),
):
    """Create a write-only agent token (prints token once)."""
    b = _brain(brain_dir)
    b.init()
    store = SQLiteStore(b.db_path)

    token_id = f"tok_{secrets.token_hex(6)}"
    raw = secrets.token_urlsafe(32)
    scopes = ["events:write"]
    store.create_api_token(
        token_id=token_id,
        created_at=datetime.now(timezone.utc).isoformat(),
        agent_id=agent,
        raw_token=raw,
        scopes=scopes,
        note=note,
    )

    console.print(
        Panel.fit(
            f"[bold]Token created[/bold]\n\n"
            f"id: {token_id}\n"
            f"agent: {agent}\n"
            f"scopes: {', '.join(scopes)}\n\n"
            f"[yellow]SAVE THIS TOKEN NOW[/yellow] (it will not be shown again):\n\n"
            f"{raw}",
            title="🧠 Second Brain",
        )
    )


@server_app.command("token-list")
def token_list(
    agent: Optional[str] = typer.Option(None, "--agent"),
    brain_dir: Optional[Path] = typer.Option(
        None, "--brain-dir", envvar="SECOND_BRAIN_DIR"
    ),
):
    """List tokens (hashes are never shown)."""
    b = _brain(brain_dir)
    b.init()
    store = SQLiteStore(b.db_path)
    rows = store.list_api_tokens(agent_id=agent)

    table = Table(title=f"API Tokens ({len(rows)})")
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Agent", style="magenta")
    table.add_column("Scopes", style="white")
    table.add_column("Created", style="cyan", no_wrap=True)
    table.add_column("Last Used", style="cyan", no_wrap=True)
    table.add_column("Revoked", style="red", no_wrap=True)

    for r in rows:
        table.add_row(
            r.get("id", ""),
            r.get("agent_id", ""),
            ",".join(r.get("scopes") or []),
            (r.get("created_at", "") or "")[:10],
            (r.get("last_used", "") or "")[:10],
            "yes" if r.get("revoked_at") else "",
        )
    console.print(table)


@server_app.command("token-revoke")
def token_revoke(
    token_id: str,
    brain_dir: Optional[Path] = typer.Option(
        None, "--brain-dir", envvar="SECOND_BRAIN_DIR"
    ),
):
    b = _brain(brain_dir)
    b.init()
    store = SQLiteStore(b.db_path)
    store.revoke_api_token(token_id, datetime.now(timezone.utc).isoformat())
    console.print(f"[green][/green] Revoked {token_id}")


@server_app.command("serve")
def serve(
    host: str = typer.Option("127.0.0.1", "--host"),
    port: int = typer.Option(8009, "--port"),
    brain_dir: Optional[Path] = typer.Option(
        None, "--brain-dir", envvar="SECOND_BRAIN_DIR"
    ),
):
    """Run the optional FastAPI server (requires `pip install second-brain[server]`)."""
    try:
        import uvicorn

        from .server import create_app
    except Exception as e:
        console.print(
            "[red]Server extra not installed.[/red] Run: `pip install second-brain[server]`"
        )
        raise typer.Exit(code=1)

    b = _brain(brain_dir)
    b.init()
    app_ = create_app(b)
    uvicorn.run(app_, host=host, port=port, log_level="info")


@app.command("session-start")
def session_start(
    agent: Optional[str] = typer.Option(None, "--agent", "-a"),
    project: Optional[str] = typer.Option(None, "--project", "-p"),
    brain_dir: Optional[Path] = typer.Option(None, "--brain-dir", envvar="SECOND_BRAIN_DIR"),
):
    """Start a new session and print its ID."""
    b = Brain(brain_dir) if brain_dir else Brain.default()
    sid = b.start_session(agent_id=agent, project=project)
    console.print(f"[bold green]Session started:[/bold green] {sid}")

@app.command("session-end")
def session_end(
    session_id: str = typer.Argument(...),
    outcome: str = typer.Option("passed", "--outcome", "-o"),
    details: Optional[str] = typer.Option(None, "--details", "-d"),
    brain_dir: Optional[Path] = typer.Option(None, "--brain-dir", envvar="SECOND_BRAIN_DIR"),
):
    """End an existing session."""
    b = Brain(brain_dir) if brain_dir else Brain.default()
    b.end_session(session_id, outcome=outcome, details=details)
    console.print(f"[bold green]Session ended:[/bold green] {session_id}")

@app.command("session-list")
def session_list(
    brain_dir: Optional[Path] = typer.Option(None, "--brain-dir", envvar="SECOND_BRAIN_DIR"),
    limit: int = typer.Option(20, "--limit", "-n"),
):
    """List recent sessions."""
    b = Brain(brain_dir) if brain_dir else Brain.default()
    rows = b._store().conn.execute(
        "SELECT id, started_at, ended_at, agent_id, project FROM sessions ORDER BY started_at DESC LIMIT ?",
        (limit,)
    ).fetchall()
    if not rows:
        console.print("[dim]No sessions found.[/dim]")
        return
    table = Table(title="Sessions")
    table.add_column("ID", style="cyan"); table.add_column("Started", style="green")
    table.add_column("Ended", style="yellow"); table.add_column("Agent"); table.add_column("Project")
    for r in rows:
        table.add_row(r["id"], r["started_at"], r["ended_at"] or "", r["agent_id"] or "", r["project"] or "")
    console.print(table)


@app.command("prune")
def prune(
    days: int = typer.Option(90, "--days", "-d", help="Delete events older than N days"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be deleted"),
    brain_dir: Optional[Path] = typer.Option(None, "--brain-dir", envvar="SECOND_BRAIN_DIR"),
):
    """Delete old events and sessions (retention policy)."""
    from second_brain import Brain
from second_brain.installer import install as cli_install
    b = Brain(brain_dir) if brain_dir else Brain.default()
    b.init()
    from datetime import datetime, timezone
    cutoff = datetime.now(timezone.utc).replace(day=datetime.now().day - days)
    cutoff_iso = cutoff.isoformat()
    store = b._store()
    with store.connect() as conn:
        evt = conn.execute("SELECT COUNT(*) FROM events WHERE ts < ?", (cutoff_iso,)).fetchone()[0]
        sess = conn.execute("SELECT COUNT(*) FROM sessions WHERE started_at < ?", (cutoff_iso,)).fetchone()[0]
        if dry_run:
            console.print(f"[yellow]Would delete:[/yellow] {evt} events, {sess} sessions older than {days} days")
            return
        if evt == 0 and sess == 0:
            console.print("[green]✓ Nothing to delete — retention policy satisfied.[/green]")
            return
        conn.execute("DELETE FROM events WHERE ts < ?", (cutoff_iso,))
        conn.execute("DELETE FROM sessions WHERE started_at < ?", (cutoff_iso,))
        conn.commit()
        console.print(f"[green]✓ Deleted:[/green] {evt} events, {sess} sessions")

@app.command("status")
def status(
    brain_dir: Optional[Path] = typer.Option(None, "--brain-dir", envvar="SECOND_BRAIN_DIR"),
):
    """Show brain health, size, and statistics."""
    from second_brain import Brain
from second_brain.installer import install as cli_install
    import os
    b = Brain(brain_dir) if brain_dir else Brain.default()
    b.init()
    store = b._store()
    db_size = os.path.getsize(b.db_path)
    key_size = os.path.getsize(b.key_path) if b.key_path.exists() else 0
    with store.connect() as conn:
        evt = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        sess = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
        cred = conn.execute("SELECT COUNT(*) FROM credentials").fetchone()[0]
        tok = conn.execute("SELECT COUNT(*) FROM api_tokens").fetchone()[0]
        last = conn.execute("SELECT MAX(ts) FROM events").fetchone()[0]
    table = Table(title="Second Brain Status")
    table.add_column("Metric"); table.add_column("Value", style="green")
    table.add_row("DB size", f"{db_size/1024:.1f} KB")
    table.add_row("Key size", f"{key_size} B")
    table.add_row("Total events", str(evt))
    table.add_row("Total sessions", str(sess))
    table.add_row("Credentials", str(cred))
    table.add_row("API tokens", str(tok))
    table.add_row("Last event", last or "never")
    console.print(table)


@app.command("install")
def install_command(
    server: bool = typer.Option(False, "--server", "-s", help="Install server mode (write-only HTTP API)"),
    token_for: Optional[str] = typer.Option(None, "--token-for", help="Create token for specified agent (server mode only)"),
    brain_dir: Optional[Path] = typer.Option(None, "--brain-dir", envvar="SECOND_BRAIN_DIR"),
):
    """Autonomous self-install: detect agent, set up brain, configure integration."""
    import os
    if brain_dir:
        os.environ["SECOND_BRAIN_DIR"] = str(brain_dir)
    sys.exit(cli_install(server_mode=server, token_for=token_for))


if __name__ == "__main__":
    app()
