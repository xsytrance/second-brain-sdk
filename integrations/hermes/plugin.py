"""Hermes Agent ⇆ Second Brain integration (official plugin).

This plugin auto-logs Hermes agent activity into a Second Brain instance.
It patches ``AIAgent`` lifecycle methods to create sessions and capture events.

Installation:
  1. Copy this directory to Hermes plugins dir:
       cp -r integrations/hermes ~/.hermes/plugins/second_brain
  2. Install Second Brain in Hermes venv:
       source ~/.hermes/hermes-agent/venv/bin/activate
       pip install second-brain
       second-brain init
  3. Restart Hermes.

Configuration (optional environment variables):
  SECOND_BRAIN_DIR            – override default (~/.second-brain)
  SECOND_BRAIN_SERVER_URL     – remote server URL (else local DB)
  SECOND_BRAIN_TOKEN          – bearer token for server mode
  HERMES_SECOND_BRAIN_DEBUG   – set "1" to enable debug logging
"""

import os
import sys
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

# --- Lazy import of Second Brain (only when plugin activates) ---
def _import_brain():
    try:
        from second_brain import Brain
        return Brain
    except ImportError as e:
        print(f"[second_brain] ERROR: Second Brain not installed: {e}")
        print("  Run: pip install second-brain")
        sys.exit(1)

# Global session cache per Hermes process
_active_session_id: str | None = None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_brain_and_session(agent_id: str, project: str | None = None) -> tuple[Any, str]:
    """Return (Brain, session_id), creating session if needed."""
    global _active_session_id
    Brain = _import_brain()
    brain_dir = os.environ.get("SECOND_BRAIN_DIR")
    brain = Brain(brain_dir) if brain_dir else Brain.default()
    brain.init()

    if _active_session_id is None:
        _active_session_id = brain.start_session(agent_id=agent_id, project=project)
        if os.environ.get("HERMES_SECOND_BRAIN_DEBUG") == "1":
            print(f"[second_brain] session started: {_active_session_id}")

    return brain, _active_session_id


def _close_session(outcome: str = "passed"):
    """End the current Hermes session."""
    global _active_session_id
    if _active_session_id is None:
        return
    Brain = _import_brain()
    brain_dir = os.environ.get("SECOND_BRAIN_DIR")
    brain = Brain(brain_dir) if brain_dir else Brain.default()
    brain.end_session(_active_session_id, outcome=outcome)
    if os.environ.get("HERMES_SECOND_BRAIN_DEBUG") == "1":
        print(f"[second_brain] session ended: {_active_session_id} (outcome={outcome})")
    _active_session_id = None


# --- Monkey-patch entry points (Hermes AIAgent class) ---

_original_init = None
_original_run_conversation = None


def register():
    """Hermes plugin entry point. Called once at Hermes startup."""
    global _original_init, _original_run_conversation
    try:
        from hermes import AIAgent  # type: ignore
    except ImportError:
        print("[second_brain] ERROR: Could not import hermes.AIAgent — are you running inside Hermes?")
        return

    # Patch AIAgent.__init__
    _original_init = AIAgent.__init__

    def _patched_init(self, *args, **kwargs):
        _original_init(self, *args, **kwargs)
        # Store original for later use
        self._second_brain_original_chat = getattr(self, 'chat', None)

    AIAgent.__init__ = _patched_init

    # Patch AIAgent.run_conversation (or .chat if that's the entry)
    _original_run_conversation = AIAgent.run_conversation

    def _patched_run_conversation(self, *args, **kwargs):
        global _active_session_id
        # Derive agent_id and project from self or call
        agent_id = getattr(self, 'agent_id', args[0] if args else None) or 'hermes-unknown'
        project = kwargs.get('project') or (args[1] if len(args) > 1 else None)
        user_id = kwargs.get('user_id') or (args[2] if len(args) > 2 else None)

        _ensure_brain_and_session(agent_id=agent_id, project=project)

        try:
            result = _original_run_conversation(self, *args, **kwargs)
            _close_session(outcome="passed")
            return result
        except Exception as e:
            _close_session(outcome="failed")
            raise

    AIAgent.run_conversation = _patched_run_conversation

    print("[second_brain] plugin loaded — logging to Second Brain")

