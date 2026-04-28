#!/usr/bin/env python3
"""Minimal example: create a Second Brain and log an event."""

from second_brain import Brain


def main():
    brain = Brain.default()
    brain.init()

    eid = brain.log_event(
        type="task_started",
        title="Quickstart event",
        project="demo",
        agent_id="example-agent",
    )
    print("logged", eid)


if __name__ == "__main__":
    main()
