#!/usr/bin/env python3
"""Auto-session wrapper for any Python script."""
import sys, os
from second_brain import Brain
def main():
    if len(sys.argv) < 2:
        print("Usage: python -m second_brain.agent_wrapper <script> [args...]")
        sys.exit(1)
    script, args = sys.argv[1], sys.argv[2:]
    brain = Brain.default(); brain.init()
    agent = os.environ.get("AGENT_NAME", os.uname().nodename)
    project = os.environ.get("PROJECT_NAME", "default")
    sid = brain.start_session(agent_id=agent, project=project)
    brain.log_event(type="task_started", title=f"Running {script}", session_id=sid, meta={"args": args})
    try:
        rc = os.system(f"python3 {script} {' '.join(args)}")
        brain.log_event(type="task_completed", title=f"Finished {script}", session_id=sid,
                        outcome="passed" if rc == 0 else "failed", meta={"exit_code": rc})
        brain.end_session(sid)
        sys.exit(rc)
    except Exception as e:
        brain.log_event(type="task_failed", title=f"Failed {script}", session_id=sid, details=str(e), outcome="failed")
        brain.end_session(sid)
        print(f"ERROR: {e}")
        sys.exit(1)
if __name__ == "__main__":
    main()
