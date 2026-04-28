"""Legacy Query API (deprecated).

Prefer querying via SQLite `Brain.list_events(...)` or a future Query builder.

This file remains as a compatibility shim.
"""

from __future__ import annotations

import warnings

warnings.warn(
    "second_brain.query is legacy; prefer Brain.list_events for new code",
    DeprecationWarning,
    stacklevel=2,
)

from .legacy.query import *  # noqa: F401,F403
