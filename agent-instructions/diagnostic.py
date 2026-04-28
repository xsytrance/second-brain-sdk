#!/usr/bin/env python3
"""Second Brain Agent Diagnostic - self-check and repair hints."""
import sys, os
from pathlib import Path
import subprocess
def run(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return r.returncode, r.stdout, r.stderr
def check(cond, ok, fail, fix=None):
    if cond: print(f"[OK] {ok}")
    else:
        print(f"[FAIL] {fail}")
        if fix: print(f"    FIX: {fix}")
    return cond
def main():
    print("=== Second Brain Agent Diagnostic ===\\n")
    py = os.system("python3 --version >/dev/null 2>&1") == 0
    check(py, "Python3 available", "Python3 missing - install python3")
    in_venv = os.environ.get("VIRTUAL_ENV") is not None
    check(in_venv, "Inside virtual environment", "Not in venv", fix="source ~/.venvs/second-brain/bin/activate")
    try:
        from second_brain import Brain
        check(True, "second_brain module importable", "Not installed", fix="pip install second-brain")
    except ImportError as e:
        check(False, "second_brain module importable", f"Import error: {e}", fix="pip install second-brain")
        return 1
    brain_dir = Path(os.environ.get("SECOND_BRAIN_DIR", Path.home() / ".second-brain"))
    db = brain_dir / "brain.db"
    key = brain_dir / "brain.key"
    check(db.exists(), f"DB exists at {brain_dir}", "DB missing", fix="second-brain init")
    check(key.exists(), f"Key exists", "Key missing - RESTORE NEEDED", fix="Restore from backup")
    try:
        b = Brain(brain_dir); b.init(); b.list_events(limit=1)
        check(True, "Database readable", "DB unreadable")
    except Exception as e:
        check(False, "Database readable", f"Error: {e}")
    if key.exists():
        mode = oct(key.stat().st_mode & 0o777)
        check(mode in ['0o600', '0o400'], f"Key permissions secure ({mode})", f"Insecure: {mode}", fix="chmod 600 ~/.second-brain/brain.key")
    srv = os.environ.get("SECOND_BRAIN_SERVER_URL")
    tok = os.environ.get("SECOND_BRAIN_TOKEN")
    if srv and tok:
        try:
            import requests
            r = requests.get(f"{srv}/health", timeout=3)
            check(r.status_code==200 and r.json().get("ok"), "Server reachable", f"Unreachable: HTTP {r.status_code}", fix="Start server on PRIME")
        except Exception as e:
            check(False, "Server reachable", f"Error: {e}")
    else:
        print("[INFO] Server mode not configured (using local DB)")
    plugin = Path.home() / ".hermes/plugins/second_brain/plugin.py"
    if plugin.exists():
        check(True, "Hermes plugin present", "Plugin missing", fix="cp -r integrations/hermes ~/.hermes/plugins/")
        try:
            import sys; sys.path.insert(0, str(plugin.parent))
            from second_brain import plugin as p
            hooks = p.register()
            check(len(hooks) > 0, "Plugin hooks registered", "No hooks returned", fix="Check plugin code / Hermes compatibility")
        except Exception as e:
            check(False, "Plugin loads", f"Error: {e}", fix="Ensure Second Brain in Hermes venv")
    else:
        print("[INFO] Hermes plugin not detected")
    print("\\n--- Test Event ---")
    try:
        b = Brain.default(); b.init()
        sid = b.start_session(agent_id="diagnostic", project="self-test")
        b.log_event(type="diagnostic", title="Agent health check", session_id=sid)
        b.end_session(sid)
        check(True, "Test event logged", "Failed to log event")
    except Exception as e:
        check(False, "Test event logged", f"Error: {e}")
    print("\\n=== Diagnostic complete ===")
    return 0
if __name__ == "__main__":
    sys.exit(main())
