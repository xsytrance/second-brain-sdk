from __future__ import annotations

import sys
from pathlib import Path

from second_brain.installer import AgentProfile, AgentType, Installer


class NonInteractiveStdin:
    def isatty(self) -> bool:
        return False


def make_installer(tmp_path: Path, *, reset: bool = False) -> Installer:
    brain_dir = tmp_path / "brain"
    brain_dir.mkdir()
    profile = AgentProfile(
        type=AgentType.GENERIC,
        home=tmp_path,
        venv_candidates=[tmp_path / "venv"],
        brain_dir=brain_dir,
    )
    installer = Installer(profile, repo_path=tmp_path / "repo", reset=reset)
    installer.repo_dir = tmp_path / "repo"
    installer.repo_dir.mkdir()
    installer.venv_bin = tmp_path / "venv" / "bin"
    installer.venv_bin.mkdir(parents=True)
    return installer


def test_same_version_noninteractive_noops_without_reset(tmp_path, monkeypatch):
    installer = make_installer(tmp_path)
    monkeypatch.setattr(installer, "_repo_version", lambda: "0.1.0")
    monkeypatch.setattr(installer, "_installed_version", lambda: "0.1.0")
    monkeypatch.setattr(sys, "stdin", NonInteractiveStdin())

    assert installer.evaluate_existing_install() == 0
    assert installer.noop_current is True
    assert installer.p.brain_dir.exists()


def test_older_version_proceeds_to_upgrade(tmp_path, monkeypatch):
    installer = make_installer(tmp_path)
    monkeypatch.setattr(installer, "_repo_version", lambda: "0.2.0")
    monkeypatch.setattr(installer, "_installed_version", lambda: "0.1.0")
    monkeypatch.setattr(sys, "stdin", NonInteractiveStdin())

    assert installer.evaluate_existing_install() == 0
    assert installer.noop_current is False
    assert installer.p.brain_dir.exists()


def test_reset_backs_up_and_removes_active_brain(tmp_path, monkeypatch):
    installer = make_installer(tmp_path, reset=True)
    marker = installer.p.brain_dir / "marker.txt"
    marker.write_text("keep me in backup")
    monkeypatch.setattr(installer, "_repo_version", lambda: "0.1.0")
    monkeypatch.setattr(installer, "_installed_version", lambda: "0.1.0")

    assert installer.evaluate_existing_install() == 0
    assert installer.noop_current is False
    assert not installer.p.brain_dir.exists()
    backups = list(tmp_path.glob(".second-brain.reset-backup.*"))
    assert len(backups) == 1
    assert (backups[0] / "marker.txt").read_text() == "keep me in backup"
