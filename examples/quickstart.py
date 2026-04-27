#!/usr/bin/env python3
"""Minimal example: create a Second Brain and log a task."""
from pathlib import Path
from second_brain_sdk import Vault, Session

# Point to brain directory (or let default)
brain_dir = Path.home() / ".hermes" / "profiles" / "snow" / "second_brain"

# Initialize vault (creates if missing)
vault = Vault(brain_dir / "vault.json.enc")

# Quick log
vault.log_event(
    event_type="milestone",
    title="SDK installed and tested",
    project="second-brain-sdk",
    tags=["setup", "dev"],
    details="Ran example script successfully",
)

print(f"✓ Event logged. Vault at {brain_dir}")
print(f"   Events so far: {len(vault._data['events'])}")
