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
from contextlib import suppress
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

# Module-level storage for original methods
_original_init: Any = None
_original_run_conversation: Any = None
_active_session_id: str | None = None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _import_brain():
    try:
        from second_brain import Brain
        return Brain
    except ImportError as e:
        print(f"[second_brain] ERROR: Second Brain not installed: {e}")
        print("  Fix: source ~/.hermes/hermes-agent/venv/bin/activate && pip install second-brain")
        sys.exit(1)


def _ensure_brain_and_session(agent_id: str, project: str | None = None) -> str:
    global _active_session_id
    Brain = _import_brain()
    brain_dir = os.environ.get("SECOND_BRAIN_DIR")
    brain = Brain(brain_dir) if brain_dir else Brain.default()
    brain.init()
    if _active_session_id is None:
        _active_session_id = brain.start_session(agent_id=agent_id, project=project)
        if os.environ.get("HERMES_SECOND_BRAIN_DEBUG") == "1":
            print(f"[second_brain] session started: {_active_session_id}")
    return _active_session_id


def _close_session(outcome: str = "passed"):
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


def on_tool_call(agent_id: str, tool_name: str, arguments: dict, session_id: str):
    Brain = _import_brain()
    brain_dir = os.environ.get("SECOND_BRAIN_DIR")
    b = Brain(brain_dir) if brain_dir else Brain.default()
    b.init()
    b.log_event(type="tool_invocation", title=f"Tool call: {tool_name}", details=f"Arguments: {arguments}",
                agent_id=agent_id, session_id=session_id, meta={"tool": tool_name, "arguments": arguments})


def on_tool_result(agent_id: str, tool_name: str, result: Any, session_id: str, error: str | None = None):
    Brain = _import_brain()
    brain_dir = os.environ.get("SECOND_BRAIN_DIR")
    b = Brain(brain_dir) if brain_dir else Brain.default()
    b.init()
    outcome = "failed" if error else "passed"
    b.log_event(type="tool_result", title=f"Tool result: {tool_name}", details=str(result) if not error else f"ERROR: {error}",
                outcome=outcome, agent_id=agent_id, session_id=session_id, meta={"tool": tool_name})


def on_llm_call(agent_id: str, model: str, messages: list, session_id: str, **kwargs):
    Brain = _import_brain()
    brain_dir = os.environ.get("SECOND_BRAIN_DIR")
    b = Brain(brain_dir) if brain_dir else Brain.default()
    b.init()
    b.log_event(type="llm_call", title=f"LLM call: {model}", details=f"Messages: {len(messages)}",
                agent_id=agent_id, session_id=session_id, meta={"model": model, "message_count": len(messages)})


def on_llm_response(agent_id: str, model: str, response: Any, session_id: str, latency_ms: int | None = None):
    Brain = _import_brain()
    brain_dir = os.environ.get("SECOND_BRAIN_DIR")
    b = Brain(brain_dir) if brain_dir else Brain.default()
    b.init()
    meta = {"model": model}
    if latency_ms is not None:
        meta["latency_ms"] = latency_ms
    b.log_event(type="llm_response", title=f"LLM response: {model}", details=str(response)[:500],
                agent_id=agent_id, session_id=session_id, meta=meta)


def register():
    """Hermes plugin entry point. Called once at Hermes startup."""
    global _original_init, _original_run_conversation
    try:
        from hermes import AIAgent  # type: ignore
    except ImportError:
        print("[second_brain] WARNING: Could not import hermes.AIAgent — plugin disabled (not inside Hermes?)")
        return {}

    _original_init = AIAgent.__init__
    _original_run_conversation = AIAgent.run_conversation

    def _patched_init(self, *args, **kwargs):
        _original_init(self, *args, **kwargs)
    AIAgent.__init__ = _patched_init

    def _patched_run_conversation(self, *args, **kwargs):
        global _active_session_id
        agent_id = getattr(self, 'agent_id', args[0] if args else None) or 'hermes-unknown'
        project = kwargs.get('project') or (args[1] if len(args) > 1 else None)
        _ensure_brain_and_session(agent_id=agent_id, project=project)
        try:
            result = _original_run_conversation(self, *args, **kwargs)
            _close_session(outcome="passed")
            return result
        except Exception:
            _close_session(outcome="failed")
            raise

    AIAgent.run_conversation = _patched_run_conversation
    print("[second_brain] plugin loaded — activity logging to Second Brain enabled")
    return {
        "on_tool_call": on_tool_call,
        "on_tool_result": on_tool_result,
        "on_llm_call": on_llm_call,
        "on_llm_response": on_llm_response,
    }
