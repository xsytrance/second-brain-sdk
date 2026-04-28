"""Second Brain CLI (standalone).

This is the public CLI entrypoint for the standalone package.

Current state:
- Uses the legacy encrypted-JSON Vault under the hood.
- We will switch the implementation to the new SQLite `Brain` core in the next phase.

Keeping this file stable avoids breaking users as internals evolve.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console
from rich.table import Table

# Temporary: legacy vault-based backend
from .core import Vault
from .credentials import CredentialManager
from .query import Query

console = Console()
app = typer.Typer(add_completion=False, help="Second Brain — standalone memory for agents")


def _default_brain_dir() -> Path:
    # Standalone default (no Hermes assumptions)
    return Path.home() / ".second-brain"


def _vault(brain_dir: Optional[Path]) -> Vault:
    bd = brain_dir or _default_brain_dir()
    bd.mkdir(parents=True, exist_ok=True)
    return Vault(str(bd / "vault.json.enc"), str(bd / "brain.key"))


@app.command()
def init(
    brain_dir: Optional[Path] = typer.Option(None, "--brain-dir", envvar="SECOND_BRAIN_DIR"),
):
    """Initialize a new brain directory."""
    bd = brain_dir or _default_brain_dir()
    bd.mkdir(parents=True, exist_ok=True)
    console.print(f"[green]✓[/green] Second Brain initialized at {bd}")
    console.print(f"Key file: {bd / 'brain.key'}")


@app.command()
def log(
    event_type: str = typer.Argument(...),
    title: str = typer.Argument(...),
    details: Optional[str] = typer.Option(None, "--details", "-d"),
    project: Optional[str] = typer.Option(None, "--project", "-p"),
    outcome: str = typer.Option("passed", "--outcome"),
    tag: List[str] = typer.Option([], "--tag", "-t"),
    session: Optional[str] = typer.Option(None, "--session"),
    brain_dir: Optional[Path] = typer.Option(None, "--brain-dir", envvar="SECOND_BRAIN_DIR"),
):
    """Log an event."""
    v = _vault(brain_dir)
    evt = v.log_event(
        event_type=event_type,
        title=title,
        details=details,
        project=project,
        outcome=outcome,
        tags=tag,
        session_id=session,
    )
    console.print(f"[green]✓[/green] Logged event {evt.id}")


@app.command()
def events(
    project: Optional[str] = typer.Option(None, "--project", "-p"),
    failed: bool = typer.Option(False, "--failed"),
    limit: int = typer.Option(20, "--limit", "-l"),
    brain_dir: Optional[Path] = typer.Option(None, "--brain-dir", envvar="SECOND_BRAIN_DIR"),
):
    """List events."""
    v = _vault(brain_dir)
    q = Query(v)
    if project:
        q = q.project(project)
    if failed:
        q = q.failed()
    rows = q.limit(limit).all()

    table = Table(title=f"Events ({len(rows)})")
    table.add_column("Time", style="cyan", no_wrap=True)
    table.add_column("Type", style="magenta")
    table.add_column("Title", style="white")
    table.add_column("Project", style="green")
    table.add_column("Outcome")

    for e in rows:
        table.add_row(
            (e.get("timestamp", "")[:16]).replace("T", " "),
            e.get("type", ""),
            e.get("title", ""),
            e.get("project", "") or "",
            e.get("outcome", ""),
        )

    console.print(table)


@app.command("credential-add")
def credential_add(
    service: str,
    kind: str,
    context: str,
    value: str = typer.Option(..., prompt=True, hide_input=True, confirmation_prompt=True),
    brain_dir: Optional[Path] = typer.Option(None, "--brain-dir", envvar="SECOND_BRAIN_DIR"),
):
    """Add an encrypted credential."""
    v = _vault(brain_dir)
    mgr = CredentialManager(v)
    cred = mgr.store(service=service, kind=kind, context=context, value=value)
    console.print(f"[green]✓[/green] Stored credential {cred.id}")


@app.callback(invoke_without_command=True)
def _main(ctx: typer.Context):
    if ctx.invoked_subcommand is None:
        console.print("Run `second-brain --help`")


if __name__ == "__main__":
    app()
