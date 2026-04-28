#!/usr/bin/env python3
"""Check Second Brain health: DB connectivity, key validity, server reachability."""

import sys
from pathlib import Path
from second_brain import Brain

def check_local():
    b = Brain.default()
    try:
        b.init()
        b.list_events(limit=1)
        print("✓ Local brain OK")
        return True
    except Exception as e:
        print(f"✗ Local brain ERROR: {e}")
        return False

def check_server():
    import os
    url = os.getenv("SECOND_BRAIN_SERVER_URL")
    token = os.getenv("SECOND_BRAIN_TOKEN")
    if not url or not token:
        print("⊘ Server mode not configured (no URL/token)")
        return None
    try:
        import requests
        resp = requests.get(f"{url}/health", timeout=3)
        if resp.status_code == 200 and resp.json().get("ok"):
            print(f"✓ Server reachable: {url}")
            return True
        print(f"✗ Server health failed: {resp.status_code}")
        return False
    except Exception as e:
        print(f"✗ Server unreachable: {e}")
        return False

if __name__ == "__main__":
    print("=== Second Brain Health Check ===\n")
    local = check_local()
    server = check_server()
    print()
    if local and (server is None or server):
        print("All checks passed")
        sys.exit(0)
    else:
        print("Some checks failed")
        sys.exit(1)
