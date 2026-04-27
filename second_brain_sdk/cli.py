"""Command-line interface for Second Brain SDK."""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table
from rich.json import JSON
from rich.panel import Panel

from .core import Vault, Event
from .session import Session
from .query import Query
from .credentials import CredentialManager

console = Console()


@click.group()
@click.option("--brain-dir", type=click.Path(), envvar="SECOND_BRAIN_DIR",
              help="Directory containing Second Brain vault")
@click.pass_context
def cli(ctx, brain_dir):
    """Second Brain SDK — your agent's persistent memory."""
    if brain_dir is None:
        brain_dir = Path.home() / ".hermes" / "profiles" / "snow" / "second_brain"
    ctx.ensure_object(dict)
    ctx.obj["brain_dir"] = Path(brain_dir)
    ctx.obj["vault"] = Vault(brain_dir / "vault.json.enc", brain_dir / "decryption_key.key")


@cli.command()
@click.pass_context
def init(ctx):
    """Initialize a new Second Brain in the given directory."""
    brain_dir: Path = ctx.obj["brain_dir"]
    brain_dir.mkdir(parents=True, exist_ok=True)
    (brain_dir / "sessions").mkdir(exist_ok=True)

    vault = Vault(brain_dir / "vault.json.enc", brain_dir / "decryption_key.key")

    console.print(f"[green]✓[/green] Second Brain initialized at {brain_dir}")
    console.print(f"[yellow]⚠[/yellow]  Back up the decryption key:")
    console.print(f"   {brain_dir / 'decryption_key.key'}")
    console.print("\nSet environment variable:")
    console.print(f"   export SECOND_BRAIN_DIR={brain_dir}")


@cli.command()
@click.argument("event_type", type=click.Choice([
    "task_started", "task_completed", "task_failed", "decision",
    "milestone", "session_end", "credential_added", "skill_created"
]))
@click.argument("title")
@click.option("--details", "-d", help="Longer description")
@click.option("--project", "-p", help="Project name")
@click.option("--outcome", type=click.Choice(["passed", "failed", "skipped"]), default="passed")
@click.option("--error", help="Error message if failed")
@click.option("--file", "files", multiple=True, help="Files changed")
@click.option("--tag", "tags", multiple=True, help="Tags")
@click.option("--session", help="Session ID")
@click.option("--next", "next_steps", multiple=True, help="Next step")
@click.pass_context
def log(ctx, event_type, title, details, project, outcome, error, files, tags, session, next_steps):
    """Log an event to the vault."""
    vault: Vault = ctx.obj["vault"]
    event = vault.log_event(
        event_type=event_type,
        title=title,
        details=details,
        project=project,
        outcome=outcome,
        error=error,
        files_changed=list(files) if files else None,
        tags=list(tags) if tags else None,
        session_id=session,
        next_steps=list(next_steps) if next_steps else None,
    )
    console.print(f"[green]✓[/green] Logged event [bold]{event.id}[/bold] — {title}")


@cli.command()
@click.option("--project", "-p", help="Filter by project")
@click.option("--tag", "-t", multiple=True, help="Filter by tag (any match)")
@click.option("--outcome", "-o", help="Filter by outcome")
@click.option("--failed", is_flag=True, help="Show only failures")
@click.option("--limit", "-l", default=20, help="Max results")
@click.pass_context
def events(ctx, project, tag, outcome, failed, limit):
    """List events from the vault."""
    vault: Vault = ctx.obj["vault"]
    q = Query(vault)
    if project:
        q = q.project(project)
    if tag:
        for t in tag:
            q = q.tag(t)
    if outcome:
        q = q.outcome(outcome)
    if failed:
        q = q.failed()

    events = q.limit(limit).all()

    table = Table(title=f"Events ({len(events)} results)")
    table.add_column("Time", style="cyan", no_wrap=True, width=16)
    table.add_column("Type", style="magenta", width=15)
    table.add_column("Title", style="white")
    table.add_column("Project", style="green", width=15)
    table.add_column("Outcome", width=8)

    for evt in events:
        ts = evt.get("timestamp", "")[:16].replace("T", " ")
        icon = {"passed": "✅", "failed": "❌", "skipped": "⏭️"}.get(evt.get("outcome"), "•")
        table.add_row(
            ts,
            evt.get("type", "").replace("_", " ").title()[:14],
            evt.get("title", "")[:40],
            evt.get("project", "")[:14],
            f"{icon} {evt.get('outcome', '')}",
        )

    console.print(table)


@cli.command()
@click.pass_context
def stats(ctx):
    """Show vault statistics."""
    vault: Vault = ctx.obj["vault"]
    stats = vault.get_statistics()

    console.print(Panel.fit(
        f"[bold]Vault Statistics[/bold]\n\n"
        f"Total Events  : {stats['total_events']}\n"
        f"  ✅ Passed   : {stats['passed']}\n"
        f"  ❌ Failed   : {stats['failed']}\n"
        f"  ⏭️  Skipped  : {stats['skipped']}\n"
        f"Credentials   : {stats['total_credentials']}\n"
        f"Skills tracked: {stats['skills_tracked']}\n"
        f"Vault created : {stats['vault_created'][:10]}",
        title="🧠 Second Brain"
    ))


@cli.group()
def credential():
    """Manage encrypted credentials."""


@credential.command("add")
@click.argument("service")
@click.argument("kind")
@click.argument("context")
@click.option("--value", prompt=True, hide_input=True, confirmation_prompt=True,
              help="Credential value (will prompt if not provided)")
@click.option("--expires", help="Expiration date (ISO)")
@click.option("--rotate", help="Rotation note")
@click.pass_context
def cred_add(ctx, service, kind, context, value, expires, rotate):
    """Add a new encrypted credential."""
    vault: Vault = ctx.obj["vault"]
    cred_mgr = CredentialManager(vault)
    cred = cred_mgr.store(
        service=service,
        kind=kind,
        context=context,
        value=value,
        expires_at=expires,
        rotation_note=rotate,
    )
    console.print(f"[green]✓[/green] Stored credential {cred.id}")
    console.print(f"   Service: {service} {kind}")
    console.print(f"   Context: {context}")


@credential.command("list")
@click.option("--service", help="Filter by service")
@click.pass_context
def cred_list(ctx, service):
    """List credential metadata (values not shown)."""
    vault: Vault = ctx.obj["vault"]
    creds = vault.find_credentials(service)

    table = Table(title=f"Credentials ({len(creds)})")
    table.add_column("ID", style="cyan", no_wrap=True, width=14)
    table.add_column("Service/Kind", style="magenta", width=22)
    table.add_column("Context", style="white")
    table.add_column("Created", width=12)
    table.add_column("Last Used", width=12)

    for cred in creds:
        cid = cred["id"][:12] + "..."
        svc = f"{cred.get('service','')} {cred.get('kind','')}"[:22]
        ctx_str = cred.get("context", "")[:30]
        created = cred.get("created_at", "")[:10]
        last_used = cred.get("last_used", "never")[:10]
        table.add_row(cid, svc, ctx_str, created, last_used)

    console.print(table)


@credential.command("get")
@click.argument("credential_id")
@click.pass_context
def cred_get(ctx, credential_id):
    """Decrypt and display a credential value."""
    vault: Vault = ctx.obj["vault"]
    value = vault.get_credential(credential_id)
    if value is None:
        console.print(f"[red]✗[/red] Credential {credential_id} not found or cannot decrypt")
        sys.exit(1)
    console.print(Panel(value, title=f"🔐 {credential_id}", border_style="green"))


@credential.command("rotate")
@click.argument("credential_id")
@click.option("--new-value", prompt=True, hide_input=True, confirmation_prompt=True,
              help="New credential value")
@click.option("--reason", default="Scheduled rotation", help="Rotation reason")
@click.pass_context
def cred_rotate(ctx, credential_id, new_value, reason):
    """Rotate (replace) an existing credential."""
    vault: Vault = ctx.obj["vault"]
    cred_mgr = CredentialManager(vault)
    try:
        new_cred = cred_mgr.rotate(credential_id, new_value, reason)
        console.print(f"[green]✓[/green] Rotated → new ID: {new_cred.id}")
    except ValueError as e:
        console.print(f"[red]✗[/red] {e}")
        sys.exit(1)


@cli.command()
@click.pass_context
def summary(ctx):
    """Generate session summary for latest session."""
    vault: Vault = ctx.obj["vault"]
    events = vault._data["events"]
    if not events:
        console.print("[yellow]No events logged yet.[/yellow]")
        return

    # Group by session_id
    from collections import defaultdict
    sessions = defaultdict(list)
    for e in events:
        sid = e.get("session_id", "no-session")
        sessions[sid].append(e)

    # Show latest session
    latest_sid = sorted(sessions.keys())[-1]
    latest_events = sessions[latest_sid]

    md = vault.export_session_summary(latest_sid)
    console.print(Panel(md, title=f"📋 Session {latest_sid}", border_style="blue"))


@cli.command()
@click.pass_context
def export(ctx):
    """Export entire vault as JSON (decrypted, for backup only)."""
    vault: Vault = ctx.obj["vault"]
    data = vault._data
    console.print(JSON(json.dumps(data, indent=2)))


@cli.command()
@click.pass_context
def info(ctx):
    """Show brain info and identity."""
    vault: Vault = ctx.obj["vault"]
    stats = vault.get_statistics()
    identity = vault.get_identity()

    console.print(Panel.fit(
        f"[bold]Second Brain[/bold]\n\n"
        f"Vault dir   : {ctx.obj['brain_dir']}\n"
        f"Version     : {vault._data.get('version', 'unknown')}\n"
        f"Created     : {vault._data.get('created_at', 'unknown')[:10]}\n\n"
        f"[bold]Statistics:[/bold]\n"
        f"  Events    : {stats['total_events']}\n"
        f"  Credentials: {stats['total_credentials']}\n"
        f"  Skills    : {stats['skills_tracked']}",
        title="🧠"
    ))

    if identity:
        agent = identity.get("agent", {})
        user = identity.get("user", {})
        console.print("\n[bold]Identity:[/bold]")
        console.print(f"  Agent: {agent.get('name','?')} — {agent.get('specialization','?')}")
        console.print(f"  User : {user.get('name','?')} (@{user.get('alias','?')}) — {user.get('location','?')}")


def main():
    cli()


if __name__ == "__main__":
    main()
