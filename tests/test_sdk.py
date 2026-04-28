"""Tests for Second Brain SDK core functionality."""
import os
import tempfile
import pytest
from pathlib import Path
from second_brain.core import Vault, Event, Credential
from second_brain.session import Session
from second_brain.query import Query
from second_brain.credentials import CredentialManager
from cryptography.fernet import Fernet


@pytest.fixture
def temp_brain():
    """Create a temporary Second Brain for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        brain_dir = Path(tmpdir) / "brain"
        brain_dir.mkdir()
        key = Fernet.generate_key()
        key_path = brain_dir / "decryption_key.key"
        key_path.write_bytes(key)
        vault = Vault(brain_dir / "vault.json.enc", key_path)
        yield vault


class TestVault:
    def test_log_event(self, temp_brain):
        vault = temp_brain
        event = vault.log_event("task_started", "Test task", project="demo")
        assert event.id
        assert event.title == "Test task"
        events = vault.get_events(project="demo")
        assert len(events) == 1
        assert events[0]["title"] == "Test task"

    def test_query_filtering(self, temp_brain):
        vault = temp_brain
        vault.log_event("task_completed", "A", project="alpha", tags=["api"])
        vault.log_event("task_failed", "B", project="beta", tags=["db"])
        vault.log_event("task_completed", "C", project="alpha", tags=["backend"])

        alpha = Query(vault).project("alpha").all()
        assert len(alpha) == 2

        failed = Query(vault).failed().all()
        assert len(failed) == 1
        assert failed[0]["title"] == "B"

        tagged = Query(vault).tag("api").all()
        assert len(tagged) == 1


class TestCredentials:
    def test_store_and_retrieve(self, temp_brain):
        vault = temp_brain
        cred_mgr = CredentialManager(vault)
        cred = cred_mgr.store("test", "api_key", "context", "secret123")
        retrieved = cred_mgr.retrieve(cred.id)
        assert retrieved == "secret123"

    def test_rotation(self, temp_brain):
        vault = temp_brain
        cred_mgr = CredentialManager(vault)
        cred = cred_mgr.store("svc", "token", "ctx", "oldvalue")
        new_cred = cred_mgr.rotate(cred.id, "newvalue", reason="test")
        assert new_cred.id != cred.id
        assert cred_mgr.retrieve(new_cred.id) == "newvalue"
        # old one should be gone
        assert cred_mgr.retrieve(cred.id) is None


class TestSession:
    def test_session_lifecycle(self, temp_brain):
        vault = temp_brain
        session = Session(vault, project="test-session")
        session.log("task_started", "Initialize", tags=["setup"])
        session.log("task_completed", "Initialize", tags=["setup"])
        summary = session.end("All done")
        assert "test-session" in summary
        assert "Initialize" in summary

    def test_task_context_manager_success(self, temp_brain):
        vault = temp_brain
        session = Session(vault, project="demo")
        with session.task("Demo task", tags=["example"]):
            pass  # succeeds
        session.end("Test complete")  # End the session
        events = vault.get_events(project="demo")
        # should have session_start, task_started, task_completed, session_end
        assert len(events) == 4
        types = [e["type"] for e in events]
        assert "session_start" in types
        assert "task_started" in types
        assert "task_completed" in types
        assert "session_end" in types
        completed = [e for e in events if e["type"] == "task_completed"]
        assert len(completed) == 1

    def test_task_context_manager_failure(self, temp_brain):
        vault = temp_brain
        session = Session(vault, project="demo")
        try:
            with session.task("Failing task", tags=["example"]):
                raise ValueError("Oops")
        except ValueError:
            pass
        session.end("Test failure complete")
        events = vault.get_events(project="demo")
        failed = [e for e in events if e["type"] == "task_failed"]
        assert len(failed) == 1
        assert "Oops" in failed[0].get("error", "")
        # Also check session_end logged
        types = [e["type"] for e in events]
        assert "session_start" in types
        assert "session_end" in types


class TestIdentity:
    def test_set_and_get_identity(self, temp_brain):
        vault = temp_brain
        vault.set_identity(
            agent={"name": "TestAgent", "role": "tester"},
            user={"name": "TestUser", "alias": "T"},
        )
        identity = vault.get_identity()
        assert identity["agent"]["name"] == "TestAgent"
        assert identity["user"]["alias"] == "T"
