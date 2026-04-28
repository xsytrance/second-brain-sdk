#!/usr/bin/env python3
"""Example workflow using the standalone SQLite Brain."""

from second_brain import Brain


def demo():
    brain = Brain.default()
    brain.init()

    brain.log_event(type="task_started", title="Start", project="demo", agent_id="agent-1")
    brain.log_event(type="task_completed", title="Finish", project="demo", agent_id="agent-1")

    events = brain.list_events(project="demo", limit=10)
    print("events:", len(events))

    cid = brain.store_credential(service="test", kind="api_key", context="demo", value="secret")
    assert brain.get_credential(cid) == "secret"


if __name__ == "__main__":
    demo()
