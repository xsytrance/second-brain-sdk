"""Second Brain CLI (standalone).

This is the public CLI entrypoint for the standalone package.

Current state (as of v0.1.x):
- Core storage is SQLite (Brain).
- Credentials are encrypted at rest (Fernet). Events are plaintext.
- Optional server mode will be added under the [server] extra.
"""

from __future__ import annotations

import secrets
from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .brain import Brain

console = Console()
app = typer.Typer(add_completion=False, help="Second Brain — standalone memory for agents")


def _brain(brain_dir: Optional[Path]) -> Brain:
    return Brain(brain_dir) if brain_dir else Brain.default()


@app.command()
def init(
    brain_dir: Optional[Path] = typer.Option(None, "--brain-dir", envvar="SECOND_BRAIN_DIR"),
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
    brain_dir: Optional[Path] = typer.Option(None, "--brain-dir", envvar="SECOND_BRAIN_DIR"),
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
    brain_dir: Optional[Path] = typer.Option(None, "--brain-dir", envvar="SECOND_BRAIN_DIR"),
):
    """List events."""
    b = _brain(brain_dir)
    rows = b.list_events(project=project, agent_id=agent, failed_only=failed, limit=limit, offset=offset)

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


@credential_app.command("add")
def cred_add(
    service: str,
    kind: str,
    context: str,
    value: str = typer.Option(..., prompt=True, hide_input=True, confirmation_prompt=True),
    expires_at: Optional[str] = typer.Option(None, "--expires"),
    rotation_note: Optional[str] = typer.Option(None, "--rotate"),
    brain_dir: Optional[Path] = typer.Option(None, "--brain-dir", envvar="SECOND_BRAIN_DIR"),
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
    brain_dir: Optional[Path] = typer.Option(None, "--brain-dir", envvar="SECOND_BRAIN_DIR"),
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
    brain_dir: Optional[Path] = typer.Option(None, "--brain-dir", envvar="SECOND_BRAIN_DIR"),
):
    b = _brain(brain_dir)
    value = b.get_credential(credential_id)
    if value is None:
        raise typer.Exit(code=1)
    console.print(Panel(value, title=f"🔐 {credential_id}", border_style="green"))


if __name__ == "__main__":
    app()
