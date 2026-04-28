#!/usr/bin/env python3
"""Example: Multiple agents writing to a shared Second Brain server."""

import os
import requests
import uuid

SERVER_URL = os.getenv("SECOND_BRAIN_SERVER_URL", "http://localhost:8009")
TOKEN = os.getenv("SECOND_BRAIN_TOKEN", "tok_dev")

def log_event(agent_id, event_type, title, project=None, **kwargs):
    payload = {
        "type": event_type,
        "title": title,
        "project": project,
        "agent_id": agent_id,
        "meta": kwargs.get("meta", {}),
        "tags": kwargs.get("tags", []),
        "session_id": kwargs.get("session_id"),
    }
    if "details" in kwargs:
        payload["details"] = kwargs["details"]
    if "outcome" in kwargs:
        payload["outcome"] = kwargs["outcome"]
    resp = requests.post(
        f"{SERVER_URL}/v1/events",
        headers={"Authorization": f"Bearer {TOKEN}"},
        json=payload,
        timeout=5,
    )
    resp.raise_for_status()
    return resp.json()["event_id"]

def main():
    agents = ["venus-worker", "pluto-scout", "prime-coordinator"]
    for agent in agents:
        sid = f"sess_{uuid.uuid4().hex[:12]}"
        log_event(agent, "session_started", f"Agent {agent} booting", "vg-clan", meta={"session_id": sid})
        log_event(agent, "task_started", "Heartbeat check", "vg-clan", session_id=sid)
        log_event(agent, "tool_invocation", "ping google DNS", "vg-clan", session_id=sid, meta={"tool": "ping", "target": "8.8.8.8"})
        log_event(agent, "tool_result", "ping result", "vg-clan", session_id=sid, outcome="passed", meta={"tool": "ping", "latency_ms": 24})
        log_event(agent, "task_completed", "Heartbeat check done", "vg-clan", session_id=sid, outcome="passed")
        log_event(agent, "session_ended", "Agent shutdown", "vg-clan", session_id=sid, outcome="passed")
    print(f"Logged events for {len(agents)} agents to {SERVER_URL}")

if __name__ == "__main__":
    main()
