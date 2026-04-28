#!/usr/bin/env python3
"""Example: Using Second Brain SDK in an AI agent workflow."""
import os
from datetime import datetime, timezone
from pathlib import Path

from second_brain import Vault, Session, CredentialManager, Query

def demo():
    # Initialize vault (will auto-create if missing)
    brain_dir = Path.home() / ".hermes" / "profiles" / "snow" / "second_brain"
    vault = Vault(brain_dir / "vault.json.enc")

    # Set identity (only needs to be done once)
    vault.set_identity(
        agent={
            "name": "Hermes",
            "personality": "warm-feminine-protective",
            "specialization": "assistant-for-Snooky",
        },
        user={
            "name": "Snooky Gomez",
            "alias": "Snow",
            "location": "Bacolod, Philippines",
        },
    )

    # Start a session for today's work
    session = Session(vault, project="Nook & Polish - April 2026 Update")

    # Log some tasks
    with session.task("Review Facebook post engagement", tags=["facebook", "analytics"]):
        # Simulated analysis
        top_post = "gelpedicure promo — 150 likes"
        session.log(
            "task_completed",
            title=f"Engagement review done — {top_post}",
            details="Checked last 10 posts, top performer identified",
            next_steps=["Schedule similar content for next week"],
        )

    # Store a credential (encrypted)
    cred_mgr = CredentialManager(vault)
    fb_token = os.environ.get("FB_PAGE_TOKEN", "demo-token-placeholder")
    cred = cred_mgr.store(
        service="facebook",
        kind="page_access_token",
        context="Nook & Polish Studio — ID 1019836827871345",
        value=fb_token,
        rotation_note="Rotate every 60 days or if compromised",
    )
    print(f"🔐 Credential stored with ID: {cred.id}")

    # Retrieve it later (decrypted)
    retrieved = cred_mgr.retrieve(cred.id)
    print(f"Token begins with: {retrieved[:20]}...")

    # Mark as used (for audit)
    cred_mgr.mark_used(cred.id)

    # Log a decision
    session.decision(
        title="Use direct Graph API instead of Zapier",
        details="Chose server-side Facebook integration for faster response and no third-party dependency.",
        reasoning="User prefers direct control; Zapier adds latency and cost.",
        alternatives=["Zapier webhook", "Zapier scheduled digest", "Manual copy-paste"],
    )

    # Reach a milestone
    session.milestone("Facebook API bridge deployed", "Endpoints live and tested")

    # End session and save summary
    summary = session.end("All objectives achieved. API tested successfully.")
    print("\n" + "="*60)
    print(summary)
    print("="*60)

    # Show stats
    stats = vault.get_statistics()
    print(f"\n🧠 Vault now contains {stats['total_events']} events and {stats['total_credentials']} credentials")

    # Query examples
    print("\n🔍 Query: All task_completed events")
    completed = Query(vault).type("task_completed").all()
    for e in completed:
        print(f"  ✅ {e['title']}")

    print("\n🔍 Query: Recent failures (if any)")
    failures = Query(vault).failed().limit(3).all()
    if failures:
        for f in failures:
            print(f"  ❌ {f['title']}: {f.get('error')}")
    else:
        print("  (none)")

if __name__ == "__main__":
    demo()
