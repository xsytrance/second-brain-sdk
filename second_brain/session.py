"""Legacy Session API (deprecated).

Prefer using explicit session_id fields with `Brain.log_event(...)`.

This file remains as a compatibility shim.
"""

from __future__ import annotations

import warnings

warnings.warn(
    "second_brain.session is legacy; use Brain for new code",
    DeprecationWarning,
    stacklevel=2,
)

from .legacy.session import *  # noqa: F401,F403
