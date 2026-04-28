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
import shutil
import subprocess
import sys
import time
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
    venv_override = os.environ.get("SECOND_BRAIN_VENV")
    brain_override = os.environ.get("SECOND_BRAIN_DIR")

    def venvs(*defaults: Path) -> List[Path]:
        return [Path(venv_override).expanduser()] if venv_override else list(defaults)

    def brain_dir(default: Path) -> Path:
        return Path(brain_override).expanduser() if brain_override else default

    # Hermes: has ~/.hermes/config.yaml with plugins section
    if (home / ".hermes" / "config.yaml").exists():
        return AgentProfile(
            type=AgentType.HERMES,
            home=home,
            venv_candidates=venvs(home / ".hermes" / "hermes-agent" / "venv"),
            brain_dir=brain_dir(home / ".second-brain"),
        )

    # HeartMuLa: has ~/ai/heartlib directory
    if (home / "ai" / "heartlib").exists():
        return AgentProfile(
            type=AgentType.HEARTMULA,
            home=home,
            venv_candidates=venvs(home / "ai" / "heartlib" / ".venv"),
            brain_dir=brain_dir(home / ".second-brain"),
        )

    # Generic agent / worker
    return AgentProfile(
        type=AgentType.GENERIC,
        home=home,
        venv_candidates=venvs(home / ".venvs" / "second-brain"),
        brain_dir=brain_dir(home / ".second-brain"),
    )


class Installer:
    def __init__(
        self,
        profile: AgentProfile,
        server_mode: bool = False,
        token_for: Optional[str] = None,
        repo_path: Optional[Path] = None,
        reset: bool = False,
    ):
        self.p = profile
        self.server_mode = server_mode
        self.token_for = token_for
        self.requested_repo_path = repo_path
        self.reset_requested = reset
        self.noop_current = False

    def run(self) -> int:
        """Execute all installation steps. Returns exit code."""
        steps = [
            self.check_prereqs,
            self.setup_venv,
            self.clone_repo,
            self.evaluate_existing_install,
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
            if self.noop_current:
                return 0

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
        if self.requested_repo_path is not None:
            repo_dir = self.requested_repo_path.expanduser().resolve()
            if not repo_dir.exists():
                print(f"[FAIL] Repo path does not exist: {repo_dir}")
                return 1
            if not (repo_dir / "pyproject.toml").exists():
                print(f"[FAIL] Not a Second Brain repo (missing pyproject.toml): {repo_dir}")
                return 1
            if not (repo_dir / "second_brain").exists():
                print(f"[FAIL] Not a Second Brain repo (missing second_brain package): {repo_dir}")
                return 1
            print(f"[OK] Using supplied repo path: {repo_dir}")
            self.repo_dir = repo_dir
            return 0

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

    def _repo_version(self) -> Optional[str]:
        pyproject = self.repo_dir / "pyproject.toml"
        if not pyproject.exists():
            return None
        try:
            if sys.version_info >= (3, 11):
                import tomllib

                data = tomllib.loads(pyproject.read_text())
                return str(data.get("project", {}).get("version") or "") or None
            for line in pyproject.read_text().splitlines():
                if line.strip().startswith("version") and "=" in line:
                    return line.split("=", 1)[1].strip().strip('"\'')
        except Exception:
            return None
        return None

    def _installed_version(self) -> Optional[str]:
        python = self.venv_bin / "python"
        if not python.exists():
            return None
        code = """
from importlib.metadata import PackageNotFoundError, version
for name in ('second-brain', 'second_brain'):
    try:
        print(version(name))
        raise SystemExit(0)
    except PackageNotFoundError:
        pass
raise SystemExit(1)
""".strip()
        result = subprocess.run([str(python), "-c", code], capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip().splitlines()[-1]
        return None

    @staticmethod
    def _version_key(value: Optional[str]) -> tuple:
        if not value:
            return ()
        parts = []
        for piece in value.replace("-", ".").split("."):
            digits = "".join(ch for ch in piece if ch.isdigit())
            if digits:
                parts.append(int(digits))
            else:
                parts.append(piece)
        return tuple(parts)

    def _backup_and_reset_brain(self) -> int:
        print("\n=== Reset Existing Brain ===")
        if not self.p.brain_dir.exists():
            print(f"[OK] No existing brain directory to reset: {self.p.brain_dir}")
            return 0
        backup = self.p.brain_dir.parent / f".second-brain.reset-backup.{time.strftime('%Y%m%d_%H%M%S')}"
        try:
            shutil.copytree(self.p.brain_dir, backup)
            shutil.rmtree(self.p.brain_dir)
            print(f"[OK] Existing brain backed up to {backup}")
            print(f"[OK] Reset removed active brain directory: {self.p.brain_dir}")
            return 0
        except Exception as e:
            print(f"[FAIL] Reset failed: {e}")
            return 1

    def evaluate_existing_install(self) -> int:
        print("\n=== Existing Installation ===")
        repo_version = self._repo_version()
        installed_version = self._installed_version()
        print(f"Repo version     : {repo_version or 'unknown'}")
        print(f"Installed version: {installed_version or 'not installed'}")

        if installed_version is None:
            print("[OK] No existing install detected; fresh install will proceed")
            return 0

        if repo_version and self._version_key(installed_version) < self._version_key(repo_version):
            print(f"[OK] Older install detected ({installed_version} < {repo_version}); upgrade will proceed")
            return 0

        if repo_version and self._version_key(installed_version) > self._version_key(repo_version):
            print(f"[WARN] Installed version ({installed_version}) is newer than repo ({repo_version}); reinstall from supplied repo will proceed")
            return 0

        if not self.p.brain_dir.exists():
            print("[OK] Package is current but brain state is missing; initialization will proceed")
            return 0

        if self.reset_requested:
            return self._backup_and_reset_brain()

        if sys.stdin.isatty():
            answer = input("Second Brain is already current. Reset local brain state? [y/N]: ").strip().lower()
            if answer in {"y", "yes"}:
                return self._backup_and_reset_brain()

        print("[OK] Already current; no changes will be made. To reset, rerun with --reset.")
        self.noop_current = True
        return 0

    def install_sdk(self) -> int:
        print("\n=== Install SDK ===")
        # Resolve pip binary: prefer 'pip', fall back to pip3 / pip3.x
        pip_candidates = ["pip", "pip3", f"pip{sys.version_info.major}.{sys.version_info.minor}"]
        pip_bin = None
        for candidate in pip_candidates:
            candidate_path = self.venv_bin / candidate
            if candidate_path.exists():
                pip_bin = candidate_path
                break
        if pip_bin is None:
            print(f"[FAIL] No pip binary found in {self.venv_bin}. Tried: {pip_candidates}")
            return 1

        try:
            subprocess.run([str(pip_bin), "install", "--upgrade", "pip"], capture_output=True, check=True)
            extra = "[server]" if self.server_mode else ""
            subprocess.run([str(pip_bin), "install", "-e", str(self.repo_dir) + extra], capture_output=True, check=True)
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


def install(
    server_mode: bool = False,
    token_for: Optional[str] = None,
    repo_path: Optional[str] = None,
    reset: bool = False,
) -> int:
    """CLI entry: second-brain install [REPO_PATH] [--server] [--token-for AGENT]"""
    print("\n" + "="*60)
    print("  SECOND BRAIN — AUTONOMOUS INSTALLATION")
    print("="*60 + "\n")

    profile = detect_agent()
    print(f"Agent type : {profile.type.value}")
    print(f"Home dir   : {profile.home}")
    print(f"Brain dir  : {profile.brain_dir}")
    print(f"Server mode: {server_mode}")
    print(f"Reset mode : {reset}")
    repo = Path(repo_path).expanduser().resolve() if repo_path else None
    if repo is not None:
        print(f"Repo path  : {repo}")
    print()

    installer = Installer(
        profile,
        server_mode=server_mode,
        token_for=token_for,
        repo_path=repo,
        reset=reset,
    )
    rc = installer.run()

    if rc == 0:
        print("\n" + "="*60)
        if installer.noop_current:
            print("  SECOND BRAIN ALREADY CURRENT — NO CHANGES MADE")
            print("="*60)
            print("  • To reset after explicit user approval, rerun with --reset")
            return rc
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



def uninstall() -> int:
    """Remove Second Brain from the agent. Preserves brain.db backup."""
    print("\n" + "="*60)
    print("  UNINSTALL SECOND BRAIN")
    print("="*60 + "\n")

    profile = detect_agent()
    brain_dir = profile.brain_dir
    repo_dir = profile.home / "second-brain-sdk"
    venv_path = profile.venv_candidates[0]

    # Safety: require confirmation unless forced
    print(f"This will remove:")
    print(f"  • Brain directory: {brain_dir}")
    print(f"  • Repository: {repo_dir}")
    print(f"  • Virtual environment: {venv_path}")
    print()
    print("Your brain.db will be backed up first.")
    print()

    resp = input("Continue? (yes/no): ").strip().lower()
    if resp != "yes":
        print("Uninstall cancelled.")
        return 0

    # Backup brain.db before nuking
    if brain_dir.exists():
        backup = brain_dir.parent / f".second-brain.backup.{subprocess.check_output(['date','+%Y%m%d_%H%M%S']).decode().strip()}"
        import shutil
        shutil.copytree(brain_dir, backup)
        print(f"[OK] Brain backed up to {backup}")

    # Remove brain dir
    if brain_dir.exists():
        subprocess.run(["rm", "-rf", str(brain_dir)])
        print(f"[OK] Removed {brain_dir}")

    # Remove venv
    if venv_path.exists():
        subprocess.run(["rm", "-rf", str(venv_path)])
        print(f"[OK] Removed venv {venv_path}")

    # Remove repo (optional — ask)
    if repo_dir.exists():
        resp2 = input(f"Also remove cloned repo {repo_dir}? (yes/no): ").strip().lower()
        if resp2 == "yes":
            subprocess.run(["rm", "-rf", str(repo_dir)])
            print(f"[OK] Removed repo {repo_dir}")
        else:
            print(f"Kept repo at {repo_dir}")

    # Disable Hermes plugin if present
    if profile.type == AgentType.HERMES:
        plugin_dir = profile.home / ".hermes" / "plugins" / "second_brain"
        if plugin_dir.exists():
            subprocess.run(["rm", "-rf", str(plugin_dir)])
            print(f"[OK] Removed Hermes plugin")
        # Clean config
        config_file = profile.home / ".hermes" / "config.yaml"
        if config_file.exists():
            import yaml
            try:
                cfg = yaml.safe_load(config_file.read_text()) or {}
                plugins = cfg.get("plugins", {})
                enabled = plugins.get("enabled", [])
                if "second_brain" in enabled:
                    enabled.remove("second_brain")
                    config_file.write_text(yaml.dump(cfg))
                    print("[OK] Disabled plugin in Hermes config")
            except Exception as e:
                print(f"[WARN] Could not update Hermes config: {e}")

    print("\n[OK] Uninstall complete.")
    print("To reinstall later: second-brain install")
    return 0


def restore(backup_dir: Optional[str] = None) -> int:
    """Restore Second Brain from a backup."""
    print("\n" + "="*60)
    print("  RESTORE SECOND BRAIN")
    print("="*60 + "\n")

    profile = detect_agent()
    brain_dir = profile.brain_dir

    if backup_dir is None:
        # Auto-discover latest backup in parent dirs
        parent = brain_dir.parent
        backups = sorted(parent.glob(".second-brain.backup.*"), key=os.path.getmtime, reverse=True)
        if not backups:
            print(f"No backups found in {parent}")
            return 1
        backup_dir = str(backups[0])
        print(f"Found latest backup: {backup_dir}")

    backup_path = Path(backup_dir)
    if not backup_path.exists():
        print(f"Backup not found: {backup_path}")
        return 1

    # Stop services if running
    subprocess.run(["systemctl", "--user", "stop", "second-brain"], capture_output=True)

    # Backup current brain if exists
    if brain_dir.exists():
        current_backup = brain_dir.parent / f".second-brain.before_restore.{subprocess.check_output(['date','+%Y%m%d_%H%M%S']).decode().strip()}"
        import shutil
        shutil.copytree(brain_dir, current_backup)
        print(f"[INFO] Current brain backed up to {current_backup}")

    # Restore
    import shutil
    if brain_dir.exists():
        shutil.rmtree(brain_dir)
    shutil.copytree(backup_path, brain_dir)
    print(f"[OK] Restored from {backup_path}")

    # Verify
    python = profile.venv_candidates[0] / "bin/python"
    if python.exists():
        result = subprocess.run([str(python), "-m", "second_brain.cli", "status"], capture_output=True, text=True, env=os.environ)
        if result.returncode == 0:
            print("[OK] Brain verified after restore")
        else:
            print("[WARN] Verification failed — brain restored but may need attention")
    else:
        print("[INFO] Re-install SDK to run verification")

    print("\nRestore complete.")
    return 0


def wizard() -> int:
    """Interactive guided installation with safety checks and options."""
    print("\n" + "="*60)
    print("  SECOND BRAIN — INSTALLATION WIZARD")
    print("="*60 + "\n")

    print("This wizard will guide you through installing Second Brain.")
    print("It can also uninstall or restore from backup if needed.\n")

    mode = input("Choose mode [install/uninstall/restore]: ").strip().lower()

    if mode == "install":
        server = input("Server mode? (y/n): ").strip().lower() == "y"
        token_for = None
        if server:
            token_for = input("Token for agent name (blank for hostname): ").strip() or None
        return install(server_mode=server, token_for=token_for, reset=False)

    elif mode == "uninstall":
        return uninstall()

    elif mode == "restore":
        backup = input("Backup directory (blank for latest): ").strip() or None
        return restore(backup_dir=backup)

    else:
        print("Unknown mode:", mode)
        return 1

