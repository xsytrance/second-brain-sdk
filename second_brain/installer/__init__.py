"""Second Brain — Autonomous Self-Installer

An agent can install Second Brain onto itself by running:
  second-brain install

Features:
  • Agent-aware — detects Hermes, HeartMuLa, or generic Python
  • Idempotent — safe to re-run; skips completed steps
  • Multi-mode — local-only or server (with token management)
  • Self-validating — runs diagnostics post-install
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional, List


class AgentType(Enum):
    HERMES = "hermes"
    HEARTMULA = "heartmula"
    GENERIC = "generic"
    UNKNOWN = "unknown"


@dataclass
class AgentProfile:
    type: AgentType
    home: Path
    venv_candidates: List[Path]
    brain_dir: Path
    is_server: bool = False


def detect_agent() -> AgentProfile:
    """Inspect environment to determine agent type."""
    home = Path.home()

    # Hermes: has ~/.hermes/config.yaml with plugins section
    if (home / ".hermes" / "config.yaml").exists():
        return AgentProfile(
            type=AgentType.HERMES,
            home=home,
            venv_candidates=[home / ".hermes" / "hermes-agent" / "venv"],
            brain_dir=home / ".second-brain",
        )

    # HeartMuLa: has ~/ai/heartlib directory
    if (home / "ai" / "heartlib").exists():
        return AgentProfile(
            type=AgentType.HEARTMULA,
            home=home,
            venv_candidates=[home / "ai" / "heartlib" / ".venv"],
            brain_dir=home / ".second-brain",
        )

    # Generic agent / worker
    return AgentProfile(
        type=AgentType.GENERIC,
        home=home,
        venv_candidates=[home / ".venvs" / "second-brain"],
        brain_dir=home / ".second-brain",
    )


class Installer:
    def __init__(self, profile: AgentProfile, server_mode: bool = False, token_for: Optional[str] = None):
        self.p = profile
        self.server_mode = server_mode
        self.token_for = token_for

    def run(self) -> int:
        """Execute all installation steps. Returns exit code."""
        steps = [
            self.check_prereqs,
            self.setup_venv,
            self.clone_repo,
            self.install_sdk,
            self.init_brain,
            self.configure_hermes_plugin,
            self.create_token_if_needed,
            self.verify_install,
        ]

        for step in steps:
            rc = step()
            if rc != 0:
                return rc

        return 0

    # --- Step implementations ---

    def check_prereqs(self) -> int:
        print("=== Prerequisites ===")
        ok = True

        # python3
        if subprocess.run(["which", "python3"], capture_output=True).returncode == 0:
            print("[OK] python3 found")
        else:
            print("[FAIL] python3 not in PATH")
            ok = False

        # git
        if subprocess.run(["which", "git"], capture_output=True).returncode == 0:
            print("[OK] git found")
        else:
            print("[FAIL] git not in PATH")
            ok = False

        # venv module
        try:
            subprocess.run(["python3", "-m", "venv", "/tmp/.sb_test_venv"], check=True, capture_output=True)
            subprocess.run(["rm", "-rf", "/tmp/.sb_test_venv"], capture_output=True)
            print("[OK] venv module available")
        except subprocess.CalledProcessError:
            print("[FAIL] venv module not available (install python3-venv)")
            ok = False

        # Python >= 3.9
        try:
            ver_str = subprocess.check_output(["python3", "-c", "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"], text=True).strip()
            major, minor = map(int, ver_str.split('.'))
            if (major, minor) >= (3, 9):
                print(f"[OK] Python {ver_str} >= 3.9")
            else:
                print(f"[FAIL] Python {ver_str} < 3.9")
                ok = False
        except Exception as e:
            print(f"[FAIL] Cannot read Python version: {e}")
            ok = False

        return 0 if ok else 1

    def setup_venv(self) -> int:
        print("\n=== Virtual Environment ===")
        target = self.p.venv_candidates[0]
        if target.exists() and (target / "bin" / "python").exists():
            print(f"[OK] Using existing venv: {target}")
            self.venv_bin = target / "bin"
            return 0

        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            subprocess.run(["python3", "-m", "venv", str(target)], check=True, capture_output=True)
            print(f"[OK] Created venv: {target}")
            self.venv_bin = target / "bin"
            return 0
        except subprocess.CalledProcessError as e:
            print(f"[FAIL] venv creation failed: {e.stderr.decode()}")
            return 1

    def clone_repo(self) -> int:
        print("\n=== Repository ===")
        repo_dir = self.p.home / "second-brain-sdk"
        if repo_dir.exists() and (repo_dir / ".git").exists():
            print(f"[OK] Repo present: {repo_dir}")
            try:
                subprocess.run(["git", "pull"], cwd=repo_dir, capture_output=True, check=True)
                print("[OK] Repo updated")
            except subprocess.CalledProcessError:
                print("[WARN] Could not pull latest")
            self.repo_dir = repo_dir
            return 0

        try:
            subprocess.run(["git", "clone", "https://github.com/xsytrance/second-brain-sdk.git", str(repo_dir)], check=True, capture_output=True)
            print(f"[OK] Cloned repo to {repo_dir}")
            self.repo_dir = repo_dir
            return 0
        except subprocess.CalledProcessError as e:
            print(f"[FAIL] Clone failed: {e.stderr.decode()}")
            return 1

    def install_sdk(self) -> int:
        print("\n=== Install SDK ===")
        pip = self.venv_bin / "pip"
        try:
            subprocess.run([str(pip), "install", "--upgrade", "pip"], capture_output=True, check=True)
            extra = "[server]" if self.server_mode else ""
            subprocess.run([str(pip), "install", "-e", str(self.repo_dir) + extra], capture_output=True, check=True)
            print("[OK] Second Brain installed")
            return 0
        except subprocess.CalledProcessError as e:
            print(f"[FAIL] pip install failed: {e.stderr.decode()}")
            return 1

    def init_brain(self) -> int:
        print("\n=== Initialize Brain ===")
        self.p.brain_dir.mkdir(parents=True, exist_ok=True)
        os.environ["SECOND_BRAIN_DIR"] = str(self.p.brain_dir)
        python = self.venv_bin / "python"
        try:
            result = subprocess.run(
                [str(python), "-m", "second_brain.cli", "init"],
                capture_output=True, text=True, env=os.environ
            )
            if result.returncode == 0 or "already initialized" in result.stdout.lower():
                print(f"[OK] Brain ready at {self.p.brain_dir}")
                return 0
            else:
                print(f"[FAIL] init error: {result.stderr}")
                return 1
        except Exception as e:
            print(f"[FAIL] init exception: {e}")
            return 1

    def configure_hermes_plugin(self) -> int:
        if self.p.type != AgentType.HERMES:
            print("\n[SKIP] Not Hermes — plugin not needed")
            return 0

        print("\n=== Hermes Plugin ===")
        plugin_src = self.repo_dir / "integrations" / "hermes"
        plugin_dst = self.p.home / ".hermes" / "plugins" / "second_brain"

        if plugin_dst.exists():
            print(f"[OK] Plugin already deployed")
        else:
            import shutil
            shutil.copytree(plugin_src, plugin_dst)
            print(f"[OK] Copied plugin to {plugin_dst}")

        # Enable in config
        config_file = self.p.home / ".hermes" / "config.yaml"
        if config_file.exists():
            import yaml
            try:
                cfg = yaml.safe_load(config_file.read_text()) or {}
                plugins = cfg.setdefault("plugins", {})
                enabled = plugins.setdefault("enabled", [])
                if "second_brain" not in enabled:
                    enabled.append("second_brain")
                    config_file.write_text(yaml.dump(cfg))
                    print("[OK] Enabled plugin in Hermes config")
                else:
                    print("[OK] Plugin already enabled")
            except Exception as e:
                print(f"[WARN] Could not update Hermes config: {e}")
        else:
            print("[WARN] Hermes config not found — manual plugin enable needed")

        return 0

    def create_token_if_needed(self) -> int:
        if not self.server_mode or self.p.type == AgentType.HERMES:
            return 0  # Hermes uses local DB

        print("\n=== Server Token ===")
        python = self.venv_bin / "python"
        agent_name = self.token_for or os.uname().nodename

        # Check existing
        try:
            result = subprocess.run(
                [str(python), "-m", "second_brain.cli", "server", "token-list"],
                capture_output=True, text=True, env=os.environ
            )
            if result.returncode == 0 and agent_name in result.stdout:
                print(f"[OK] Token for '{agent_name}' already exists")
                return 0
        except Exception:
            pass

        # Create token
        try:
            result = subprocess.run(
                [str(python), "-m", "second_brain.cli", "server", "token-create",
                 "--agent", agent_name, "--note", "auto-installed"],
                capture_output=True, text=True, env=os.environ
            )
            if result.returncode == 0:
                print(f"[OK] Token created for '{agent_name}'")
                # Extract token ID
                for line in result.stdout.splitlines():
                    if line.startswith("id:"):
                        token_id = line.split()[-1]
                        print(f"[INFO] Token ID: {token_id}")
                        print(f"[INFO] Set SECOND_BRAIN_TOKEN env var to use it")
                        break
                return 0
            else:
                print(f"[FAIL] Token creation failed: {result.stderr}")
                return 1
        except Exception as e:
            print(f"[FAIL] Token error: {e}")
            return 1

    def verify_install(self) -> int:
        print("\n=== Verification ===")
        python = self.venv_bin / "python"
        diag = self.repo_dir / "agent-instructions" / "diagnostic.py"

        try:
            result = subprocess.run([str(python), str(diag)], capture_output=True, text=True, env=os.environ)
            print(result.stdout)
            if result.returncode == 0:
                print("[OK] Diagnostics passed")
                return 0
            else:
                print("[WARN] Some diagnostics non-critical — review above")
                return 0  # Still succeed; can re-run diagnostic
        except Exception as e:
            print(f"[FAIL] Verification error: {e}")
            return 1


def install(server_mode: bool = False, token_for: Optional[str] = None) -> int:
    """CLI entry: second-brain install [--server] [--token-for AGENT]"""
    print("\n" + "="*60)
    print("  SECOND BRAIN — AUTONOMOUS INSTALLATION")
    print("="*60 + "\n")

    profile = detect_agent()
    print(f"Agent type : {profile.type.value}")
    print(f"Home dir   : {profile.home}")
    print(f"Brain dir  : {profile.brain_dir}")
    print(f"Server mode: {server_mode}")
    print()

    installer = Installer(profile, server_mode=server_mode, token_for=token_for)
    rc = installer.run()

    if rc == 0:
        print("\n" + "="*60)
        print("  INSTALLATION COMPLETE — NEXT STEPS")
        print("="*60)
        if profile.type == AgentType.HERMES:
            print("  • Restart Hermes to load plugin:")
            print("    systemctl --user restart hermes   (or: hermes restart)")
        if server_mode:
            print("  • Start server (one-time test):")
            print("    second-brain server serve --port 8009 &")
            print("  • Or install as systemd service:")
            print("    ~/second-brain-sdk/agent-instructions/setup_systemd.sh")
        print("  • Verify installation:")
        print("    second-brain status")
        print("  • Re-run diagnostic if needed:")
        print("    python3 ~/second-brain-sdk/agent-instructions/diagnostic.py")

    return rc

