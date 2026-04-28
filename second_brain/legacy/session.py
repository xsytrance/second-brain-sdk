"""Session tracking and automatic summarization."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from .core import Event, Vault


class Session:
    """Represents a single work session; tracks events and generates summaries."""

    def __init__(
        self,
        vault: Vault,
        project: str,
        session_id: Optional[str] = None,
        auto_summarize: bool = True,
    ):
        self.vault = vault
        self.project = project
        self.session_id = (
            session_id
            or f"sess_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{os.urandom(3).hex()}"
        )
        self.start_time = datetime.now(timezone.utc)
        self.auto_summarize = auto_summarize
        self._events: List[Event] = []

        # Log session start
        self.log(
            event_type="session_start",
            title=f"Session started — {project}",
            details=f"Session {self.session_id} initiated",
            outcome="passed",
        )

    def log(
        self,
        event_type: str,
        title: str,
        details: Optional[str] = None,
        outcome: str = "passed",
        error: Optional[str] = None,
        files_changed: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        next_steps: Optional[List[str]] = None,
    ) -> Event:
        """Log an event within this session."""
        event = self.vault.log_event(
            event_type=event_type,
            title=title,
            details=details,
            project=self.project,
            outcome=outcome,
            error=error,
            files_changed=files_changed,
            tags=tags,
            session_id=self.session_id,
            next_steps=next_steps,
        )
        self._events.append(event)
        return event

    def task(
        self,
        title: str,
        details: Optional[str] = None,
        files_changed: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        next_steps: Optional[List[str]] = None,
    ):
        """Context manager to log a task with its success/failure."""

        class TaskContext:
            def __init__(
                self,
                session: Session,
                title: str,
                details: str,
                files: List[str],
                tags: List[str],
                steps: List[str],
            ):
                self.session = session
                self.title = title
                self.details = details
                self.files = files or []
                self.tags = tags or []
                self.steps = steps or []
                self.success = True
                self.error_msg: Optional[str] = None

            def __enter__(self):
                self.session.log(
                    "task_started", self.title, self.details, tags=self.tags
                )
                return self

            def __exit__(self, exc_type, exc_val, exc_tb):
                if exc_type:
                    self.success = False
                    self.error_msg = str(exc_val)
                    self.session.log(
                        "task_failed",
                        self.title,
                        details=self.details,
                        error=self.error_msg,
                        files_changed=self.files,
                        tags=self.tags,
                        next_steps=self.steps,
                        outcome="failed",
                    )
                else:
                    self.session.log(
                        "task_completed",
                        self.title,
                        details=self.details,
                        files_changed=self.files,
                        tags=self.tags,
                        next_steps=self.steps,
                        outcome="passed",
                    )

        return TaskContext(self, title, details, files_changed, tags, next_steps)

    def decision(
        self,
        title: str,
        details: str,
        reasoning: Optional[str] = None,
        alternatives: Optional[List[str]] = None,
    ) -> Event:
        """Log a decision with context."""
        full_details = details
        if reasoning:
            full_details += f"\n\n**Reasoning:** {reasoning}"
        if alternatives:
            full_details += "\n\n**Alternatives considered:**"
            for alt in alternatives:
                full_details += f"\n- {alt}"
        return self.log(
            "decision",
            title=title,
            details=full_details,
            tags=["decision"],
        )

    def milestone(
        self,
        title: str,
        details: Optional[str] = None,
    ) -> Event:
        """Log a milestone achievement."""
        return self.log(
            "milestone",
            title=f"🎯 {title}",
            details=details,
            tags=["milestone"],
        )

    def end(self, summary: Optional[str] = None) -> str:
        """End the session, generate summary, return markdown."""
        duration = datetime.now(timezone.utc) - self.start_time
        mins = int(duration.total_seconds() // 60)
        secs = int(duration.total_seconds() % 60)

        # Log session end
        self.log(
            "session_end",
            title=f"Session ended — {self.project}",
            details=f"Duration: {mins}m {secs}s. {summary or 'Session complete.'}",
            outcome="passed",
        )

        # Generate summary markdown
        summary_md = self._build_summary(summary, mins, secs)
        return summary_md

    def _build_summary(self, summary: Optional[str], mins: int, secs: int) -> str:
        """Build the session summary markdown."""
        # Convert Event objects to dicts for sorting
        events_serialized = [
            e.to_dict() if hasattr(e, "to_dict") else e for e in self._events
        ]
        events_serialized.sort(key=lambda e: e.get("timestamp", ""))

        outcome_counts = {"passed": 0, "failed": 0, "skipped": 0}
        for e in events_serialized:
            outcome = e.get("outcome", "passed")
            outcome_counts[outcome] = outcome_counts.get(outcome, 0) + 1

        lines = [
            f"# Session {self.session_id}",
            f"\n**Duration:** {mins}m {secs}s",
            f"**Project:** {self.project}",
            f"**Events logged:** {len(events_serialized)}",
            f"**Outcomes:** passed={outcome_counts['passed']} failed={outcome_counts['failed']} skipped={outcome_counts['skipped']}",
            f"\n---\n",
        ]

        if summary:
            lines.append(f"## Summary\n\n{summary}\n")

        lines.append("## Event Log\n")
        for evt in events_serialized:
            icon = {
                "passed": "✅",
                "failed": "❌",
                "skipped": "⏭️",
                "session_start": "🚀",
                "session_end": "🏁",
            }.get(evt.get("outcome", "passed"), "•")
            type_label = evt.get("type", "").replace("_", " ").title()
            lines.append(f"{icon} **[{type_label}]** {evt['title']}")
            if evt.get("error"):
                lines.append(f"   > Error: {evt['error']}")
            if evt.get("files_changed"):
                for f in evt["files_changed"]:
                    lines.append(f"   📄 {f}")
            if evt.get("next_steps"):
                lines.append("   Next steps:")
                for step in evt["next_steps"]:
                    lines.append(f"     • {step}")
            lines.append("")

        return "\n".join(lines)

    def save_summary(self, output_dir: Optional[str] = None) -> str:
        """Save summary to a markdown file and return the path."""
        md = self.end()
        if output_dir is None:
            # Standalone default (no Hermes assumptions)
            output_dir = Path.home() / ".second-brain" / "sessions"
        else:
            output_dir = Path(output_dir)

        output_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{datetime.now(timezone.utc).strftime('%Y-%m-%d_%H%M')}_{self.session_id}.md"
        filepath = output_dir / filename

        with open(filepath, "w") as f:
            f.write(md)

        # Also update index (simplified)
        index_path = output_dir.parent / "index.md"
        if index_path.exists():
            with open(index_path) as f:
                index = f.read()
            entry = f"\n**[{datetime.now().strftime('%H:%M')}]** {self.project} — {len(self._events)} events. [Full log →](sessions/{filename})\n"
            # Insert under today's date
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            if f"## {today}" in index:
                parts = index.split(f"## {today}")
                index = f"## {today}{entry}{parts[1]}"
            else:
                index = index.rstrip() + f"\n\n## {today}\n\n{entry}"
            with open(index_path, "w") as f:
                f.write(index)

        return str(filepath)
