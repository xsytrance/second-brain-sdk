"""Query interface for filtering and searching vault events."""
from typing import Optional, List, Dict, Any
from datetime import datetime
from .core import Vault


class Query:
    """Fluent query builder for vault events."""

    def __init__(self, vault: Vault):
        self.vault = vault
        self._filters = []

    def filter(self, field: str, value: Any) -> "Query":
        """Add an exact-match filter."""
        self._filters.append(("eq", field, value))
        return self

    def project(self, name: str) -> "Query":
        """Filter by project name."""
        return self.filter("project", name)

    def tag(self, tag: str) -> "Query":
        """Filter by tag (any match)."""
        self._filters.append(("tag", "tags", tag))
        return self

    def outcome(self, outcome: str) -> "Query":
        """Filter by outcome (passed/failed/skipped)."""
        return self.filter("outcome", outcome)

    def since(self, date_str: str) -> "Query":
        """Filter events after given ISO date string."""
        self._filters.append(("gte", "timestamp", date_str))
        return self

    def until(self, date_str: str) -> "Query":
        """Filter events before given ISO date string."""
        self._filters.append(("lte", "timestamp", date_str))
        return self

    def type(self, event_type: str) -> "Query":
        """Filter by event type."""
        return self.filter("type", event_type)

    def failed(self) -> "Query":
        """Convenience: only failed events."""
        return self.outcome("failed")

    def passed(self) -> "Query":
        """Convenience: only passed events."""
        return self.outcome("passed")

    def limit(self, n: int) -> "Query":
        """Limit results."""
        self._limit = n
        return self

    def _matches(self, event: Dict[str, Any]) -> bool:
        """Check if event matches all filters."""
        for op, field, value in self._filters:
            evt_val = event.get(field)
            if op == "eq":
                if evt_val != value:
                    return False
            elif op == "tag":
                tags = event.get("tags", [])
                if value not in tags:
                    return False
            elif op == "gte":
                if evt_val is None or evt_val < value:
                    return False
            elif op == "lte":
                if evt_val is None or evt_val > value:
                    return False
        return True

    def all(self) -> List[Dict[str, Any]]:
        """Execute query and return all matching events."""
        events = self.vault._data["events"]
        filtered = [e for e in events if self._matches(e)]
        # Sort newest first
        filtered.sort(key=lambda e: e.get("timestamp", ""), reverse=True)
        if hasattr(self, "_limit"):
            return filtered[: self._limit]
        return filtered

    def first(self) -> Optional[Dict[str, Any]]:
        """Return first matching event or None."""
        results = self.limit(1).all()
        return results[0] if results else None

    def count(self) -> int:
        """Count matching events without loading them all."""
        return len(self.all())

    # ── Preset queries ────────────────────────────────────────────────────

    @classmethod
    def recent_failures(cls, vault: Vault, hours: int = 24) -> List[Dict[str, Any]]:
        """Get failures from last N hours."""
        from datetime import datetime, timedelta, timezone
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
        return Query(vault).outcome("failed").since(cutoff).all()

    @classmethod
    def by_project(cls, vault: Vault, project: str) -> List[Dict[str, Any]]:
        """Get all events for a project."""
        return Query(vault).project(project).all()

    @classmethod
    def milestone_timeline(cls, vault: Vault) -> List[Dict[str, Any]]:
        """Get all milestone events in chronological order."""
        q = Query(vault).tag("milestone")
        events = q.all()
        return sorted(events, key=lambda e: e.get("timestamp", ""))
