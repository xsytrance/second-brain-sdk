#!/usr/bin/env python3
"""Hermes Agent — Second Brain integration example.

This shows how the Second Brain SDK could be woven into Hermes's lifecycle:
- Load brain at startup
- Begin session on each new conversation
- Auto-log tasks during tool execution
- End session with summary at disconnect

To use in production, this would be integrated into hermes_tools.py or agent core.
"""
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from second_brain_sdk import Vault, Session, CredentialManager, Query


class HermesWithMemory:
    """Example Hermes agent instance with persistent memory."""

    def __init__(self, profile: str = "snow"):
        self.profile = profile
        self.brain_dir = Path.home() / ".hermes" / "profiles" / profile / "second_brain"
        self.vault = Vault(self.brain_dir / "vault.json.enc")
        self.session: Optional[Session] = None

        # Ensure identity exists
        if not self.vault.get_identity():
            self._init_identity()

        print(f"🧠 Hermes memory loaded from {self.brain_dir}")

    def _init_identity(self):
        """Store agent + user identity in vault."""
        self.vault.set_identity(
            agent={
                "name": "Hermes",
                "personality_traits": ["warm", "feminine", "protective", "practical", "empowering"],
                "communication_style": "gentle humor, direct when needed, Filipino superheroine spirit",
                "creator": "Nous Research",
                "specialization": f"assistant-for-{self.profile.capitalize()}",
            },
            user={
                "name": "Snooky Gomez",
                "alias": "Snow",
                "birthdate": "1992-06-12",
                "location": "Bacolod, Philippines",
                "partner": "Agenor",
                "current_focus": ["Nook & Polish API", "ComfyUI images", "K-1 visa", "garden", "Agenor visit"],
                "planning_categories": ["business", "beauty", "visa", "garden", "love", "life"],
            },
        )
        print("✓ Identity initialized in vault")

    def begin_conversation(self, topic: str) -> str:
        """Start a new conversation session."""
        self.session = Session(self.vault, project=topic)
        session_id = self.session.session_id
        print(f"🚀 Session started: {session_id}")
        return session_id

    # ── Example task wrappers ──────────────────────────────────────────────

    def post_to_facebook(self, message: str) -> dict:
        """Example: log when posting to Facebook."""
        with self.session.task(
            title=f'Post to Facebook: "{message[:40]}..."',
            tags=["facebook", "publish"],
            next_steps=["Verify post appeared on page"],
        ):
            # In real Hermes, this would call the actual Flask endpoint
            result = {"success": True, "post_id": "123_456"}
            return result

    def fetch_facebook_posts(self) -> list:
        """Example: log when fetching posts for context."""
        with self.session.task(
            title="Fetch recent Facebook posts",
            tags=["facebook", "read"],
        ):
            # Call actual /api/facebook/posts
            posts = [{"message": "Sample post", "created_time": datetime.now().isoformat()}]
            return posts

    def generate_image(self, prompt: str) -> str:
        """Example: log ComfyUI image generation."""
        with self.session.task(
            title=f"Generate image: {prompt[:50]}",
            tags=["comfyui", "image-gen"],
        ):
            # Call ComfyUI REST API
            filename = "generated_001.png"
            return filename

    # ── End of conversation ───────────────────────────────────────────────

    def end_conversation(self, summary: str = "") -> str:
        """End session, generate and return summary."""
        if not self.session:
            return "No active session"

        summary_md = self.session.end(summary)
        saved_path = self.session.save_summary()
        print(f"📋 Session summary saved to {saved_path}")
        return summary_md

    # ── Utility ────────────────────────────────────────────────────────────

    def log_decision(self, title: str, details: str, reasoning: str = "", alternatives: list = None):
        """Log an important decision."""
        if not self.session:
            raise RuntimeError("No active session")
        self.session.decision(title=title, details=details, reasoning=reasoning, alternatives=alternatives)

    def log_milestone(self, title: str, details: str = ""):
        """Celebrate a milestone!"""
        if not self.session:
            raise RuntimeError("No active session")
        self.session.milestone(title, details)

    def store_credential(self, service: str, kind: str, context: str, value: str) -> str:
        """Securely store a credential."""
        cred_mgr = CredentialManager(self.vault)
        cred = cred_mgr.store(service, kind, context, value)
        return cred.id

    def recent_failures(self, hours: int = 24) -> list:
        """Check recent failures (for debugging)."""
        return Query.recent_failures(self.vault, hours=hours)


# ── Demo ───────────────────────────────────────────────────────────────────

def demo_hermes_integration():
    """Simulate a Hermes agent conversation with Second Brain."""
    print("=" * 60)
    print("Hermes + Second Brain — Integration Demo")
    print("=" * 60)

    hermes = HermesWithMemory(profile="snow")

    # Start conversation
    hermes.begin_conversation("Nook & Polish — April Content Planning")

    # Log some work
    hermes.log_decision(
        title="Use direct Facebook Graph API over Zapier",
        details="Chose server-side integration for lower latency and full control.",
        reasoning="User wants assistant to post directly, not auto-archive everything.",
        alternatives=["Zapier webhook", "Manual copy-paste", "Buffer API"],
    )

    hermes.post_to_facebook("New client special this week! 💅")
    hermes.fetch_facebook_posts()
    hermes.generate_image("A nail art design with spring flowers, pastel colors")

    hermes.log_milestone("Facebook API bridge deployed and tested")

    # End conversation
    summary = hermes.end_conversation(
        "Deployed Facebook API endpoints (read + publish). Generated test post. "
        "ComfyUI image generation verified. Hub password updated to Gomez143!. "
        "Skills saved: facebook-graph-api-bridge-flask, comfyui-local-image-generation."
    )
    print("\n" + summary)
    print("\n" + "=" * 60)
    print("✅ Demo complete. Check your Second Brain sessions/ directory.")
    print("=" * 60)


if __name__ == "__main__":
    demo_hermes_integration()
