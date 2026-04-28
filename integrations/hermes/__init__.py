"""Second Brain Hermes plugin.

Logs Hermes lifecycle, LLM, and tool events into the installed second-brain SDK.
"""

from __future__ import annotations

from typing import Any


def _brain():
    from second_brain import Brain

    b = Brain.default()
    b.init()
    return b


def register(ctx) -> None:
    active_session_id: str | None = None

    def ensure_session(session_id: str | None = None, project: str | None = None) -> str | None:
        nonlocal active_session_id
        if active_session_id:
            return active_session_id
        try:
            b = _brain()
            if session_id and str(session_id).startswith("sess_"):
                active_session_id = session_id
            else:
                active_session_id = b.start_session(agent_id="hermes", project=project)
            return active_session_id
        except Exception:
            return None

    def on_session_start(session_id: str = "", platform: str = "", **kwargs: Any) -> None:
        sid = ensure_session(session_id=session_id or None, project=platform or None)
        if not sid:
            return
        try:
            _brain().log_event(
                type="session_started_hook",
                title="Hermes session hook started",
                agent_id="hermes",
                session_id=sid,
                tags=["hermes", "session", "start"],
                meta={"platform": platform, "source_session_id": session_id},
            )
        except Exception:
            pass

    def on_session_end(completed: bool = True, interrupted: bool = False, **kwargs: Any) -> None:
        nonlocal active_session_id
        sid = active_session_id or kwargs.get("session_id")
        if not sid:
            return
        try:
            outcome = "failed" if interrupted or not completed else "passed"
            _brain().end_session(str(sid), outcome=outcome)
        except Exception:
            pass
        finally:
            active_session_id = None

    def on_session_finalize(**kwargs: Any) -> None:
        sid = active_session_id or kwargs.get("session_id")
        if not sid:
            return
        try:
            _brain().log_event(
                type="session_finalized",
                title="Hermes session finalized",
                agent_id="hermes",
                session_id=str(sid),
                tags=["hermes", "session", "final"],
            )
        except Exception:
            pass

    def pre_tool_call(tool_name: str = "", args: dict | None = None, tool_call_id: str = "", task_id: str = "", session_id: str = "", **kwargs: Any) -> None:
        sid = ensure_session(session_id=session_id or None)
        try:
            _brain().log_event(
                type="tool_called",
                title=f"Call tool: {tool_name}",
                details=str(args or {})[:1000],
                agent_id="hermes",
                session_id=sid,
                tags=["hermes", "tool", tool_name],
                meta={"tool_call_id": tool_call_id, "task_id": task_id},
            )
        except Exception:
            pass

    def post_tool_call(tool_name: str = "", args: dict | None = None, result: Any = None, tool_call_id: str = "", success: bool = True, session_id: str = "", **kwargs: Any) -> None:
        sid = ensure_session(session_id=session_id or None)
        try:
            _brain().log_event(
                type="tool_completed",
                title=f"Tool: {tool_name}",
                details=str(result)[:1000],
                outcome="passed" if success else "failed",
                agent_id="hermes",
                session_id=sid,
                tags=["hermes", "tool", tool_name],
                meta={"tool_call_id": tool_call_id, "success": success},
            )
        except Exception:
            pass

    def pre_llm_call(messages: list | None = None, model: str = "", session_id: str = "", **kwargs: Any) -> None:
        sid = ensure_session(session_id=session_id or None)
        try:
            msg_count = len(messages or [])
            _brain().log_event(
                type="llm_call",
                title=f"LLM call: {model or 'unknown'}",
                details=f"messages={msg_count}",
                agent_id="hermes",
                session_id=sid,
                tags=["hermes", "llm", "call"],
                meta={"model": model, "message_count": msg_count},
            )
        except Exception:
            pass

    def post_llm_call(messages: list | None = None, model: str = "", response: Any = None, session_id: str = "", **kwargs: Any) -> None:
        sid = ensure_session(session_id=session_id or None)
        try:
            _brain().log_event(
                type="llm_response",
                title=f"LLM response: {model or 'unknown'}",
                details=str(response)[:1000],
                agent_id="hermes",
                session_id=sid,
                tags=["hermes", "llm", "response"],
                meta={"model": model},
            )
        except Exception:
            pass

    ctx.register_hook("on_session_start", on_session_start)
    ctx.register_hook("on_session_end", on_session_end)
    ctx.register_hook("on_session_finalize", on_session_finalize)
    ctx.register_hook("pre_tool_call", pre_tool_call)
    ctx.register_hook("post_tool_call", post_tool_call)
    ctx.register_hook("pre_llm_call", pre_llm_call)
    ctx.register_hook("post_llm_call", post_llm_call)
