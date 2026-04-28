"""
End-to-end verification suite for Second Brain.

Tests three core pillars:
1. agent_wrapper.py — automatic session logging for any Python script
2. second-brain CLI — token lifecycle + server commands
3. HTTP API — bearer-token write path to shared brain.db

Run with: python -m tests.e2e_verify
(ensure `second-brain install` has been run in the current environment)
"""

from __future__ import annotations

import os, sys, time, signal, subprocess, sqlite3, hashlib, json
from pathlib import Path
from typing import Optional

import requests

# ── Config ──────────────────────────────────────────────────────────────────
PYTHON = sys.executable
REPO_ROOT = Path(__file__).resolve().parents[1]
TEST_DIR = Path(os.environ.get("SECOND_BRAIN_DIR", Path.home() / ".second-brain-e2e"))
WRAPPER = REPO_ROOT / "agent-instructions" / "agent_wrapper.py"
TEST_TASK_SCRIPT = REPO_ROOT / "agent-instructions" / "test_task.py"

# ── Helpers ────────────────────────────────────────────────────────────────
def kill_on_port(port: int) -> None:
    out = subprocess.run(["lsof", "-ti", f":{port}"], capture_output=True, text=True)
    if out.stdout.strip():
        subprocess.run(["kill", "-9"] + out.stdout.split(), capture_output=True)
        time.sleep(0.5)


def wait_port(port: int, timeout: int = 5) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            requests.get(f"http://127.0.0.1:{port}/health", timeout=1)
            return True
        except Exception:
            time.sleep(0.3)
    return False


def db_connect() -> sqlite3.Connection:
    return sqlite3.connect(str(TEST_DIR / "brain.db"))


# ── Phases ──────────────────────────────────────────────────────────────────
def phase1_wrapper() -> str:
    """Run a simple Python script through agent_wrapper and verify DB rows."""
    print("\n## Phase 1: agent_wrapper integration")

    if TEST_DIR.exists():
        shutil.rmtree(TEST_DIR)
    TEST_DIR.mkdir(parents=True)

    env = os.environ.copy()
    env["SECOND_BRAIN_DIR"] = str(TEST_DIR)

    result = subprocess.run(
        [PYTHON, str(WRAPPER), str(TEST_TASK_SCRIPT)],
        capture_output=True, text=True, env=env
    )
    assert result.returncode == 0, f"Wrapper exited {result.returncode}: {result.stderr}"
    print("  ✓ Wrapper exited 0")

    conn = db_connect()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM sessions")
    assert cur.fetchone()[0] >= 1, "No session record found"
    print("  ✓ Session row exists")

    cur.execute("SELECT type, COUNT(*) FROM events GROUP BY type")
    counts = {row[0]: row[1] for row in cur.fetchall()}
    for key in ("session_started", "task_started", "task_completed", "session_ended"):
        assert counts.get(key, 0) >= 1, f"Missing event {key}"
    print(f"  ✓ Events recorded ({', '.join(f'{k}={v}' for k,v in counts.items())})")
    conn.close()
    return "ok"


def phase2_cli_token_and_server() -> str:
    """Create an agent token, start the FastAPI server, POST an event."""
    print("\n## Phase 2: CLI token lifecycle + server API")

    env = os.environ.copy()
    env["SECOND_BRAIN_DIR"] = str(TEST_DIR)

    result = subprocess.run(
        [PYTHON, "-m", "second_brain.cli", "server", "token-create",
         "--agent", "e2e-tester", "--note", "E2E integration token"],
        capture_output=True, text=True, env=env
    )
    assert result.returncode == 0, f"token-create failed: {result.stderr}"
    print("  ✓ Token created via CLI")

    import re
    m = re.search(r'([A-Za-z0-9_-]{20,})\s+$', result.stdout, re.MULTILINE)
    assert m, "Could not extract token string from CLI output"
    raw_token = m.group(1)
    print(f"  ✓ Token extracted: {raw_token[:10]}…")

    conn = db_connect()
    cur = conn.cursor()
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    cur.execute("SELECT id FROM api_tokens WHERE token_hash = ?", (token_hash,))
    row = cur.fetchone()
    assert row is not None, "Token hash not found in api_tokens"
    print(f"  ✓ Token hash confirmed in DB ({row[0]})")
    conn.close()

    kill_on_port(8009)
    server_log = TEST_DIR / "server.log"
    with open(server_log, "w") as out, open(server_log.with_suffix(".err"), "w") as err:
        server_proc = subprocess.Popen(
            [PYTHON, "-m", "second_brain.cli", "server", "serve",
             "--host", "127.0.0.1", "--port", "8009"],
            stdout=out, stderr=err, env=env, start_new_session=True
        )
    try:
        assert wait_port(8009), "Server did not become healthy within 5 s"
        print("  ✓ Server listening on 127.0.0.1:8009")

        payload = {
            "type": "e2e_programmatic",
            "title": "E2E HTTP POST verification",
            "project": "integration-test",
            "outcome": "passed",
            "meta": {"phase": "cli_server", "token_id": "tok_e2e"}
        }
        headers = {"Authorization": f"Bearer {raw_token}"}
        r = requests.post("http://127.0.0.1:8009/v1/events", json=payload, headers=headers, timeout=5)
        assert r.status_code == 200, f"POST failed ({r.status_code}): {r.text}"
        evt_id = r.json()["event_id"]
        print(f"  ✓ Event written via API — id {evt_id}")

        conn = db_connect()
        cur = conn.cursor()
        cur.execute("SELECT type, title, project FROM events WHERE id = ?", (evt_id,))
        row = cur.fetchone()
        assert row is not None, "Event not found in DB by id"
        assert row[0] == "e2e_programmatic", f"Wrong type: {row[0]}"
        print(f"  ✓ Event persisted in DB — {row}")
        conn.close()

    finally:
        server_proc.send_signal(signal.SIGTERM)
        server_proc.wait(timeout=5)
        print("  ✓ Server stopped")

    return "ok"


def main() -> int:
    print("=" * 44)
    print("  Second Brain — End-to-End Verification")
    print("=" * 44)

    try:
        phase1_wrapper()
        phase2_cli_token_and_server()
        print("\n## ALL CHECKS PASSED ✓  — SDK is operational")
        return 0
    except AssertionError as e:
        print(f"\n## ASSERTION FAILED — {e}")
        return 1
    except Exception as exc:
        print(f"\n## UNHANDLED ERROR — {exc!r}")
        import traceback; traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
