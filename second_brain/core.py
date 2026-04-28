"""Legacy Vault API (deprecated).

The standalone package has migrated to SQLite-backed `Brain`.

Prefer:
    from second_brain import Brain

This file remains as a compatibility shim.
"""

from __future__ import annotations

import warnings

warnings.warn(
    "second_brain.core (Vault) is legacy; use second_brain.Brain for new code",
    DeprecationWarning,
    stacklevel=2,
)

from .legacy.core import *  # noqa: F401,F403
