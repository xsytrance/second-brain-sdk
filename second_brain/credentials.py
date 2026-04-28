"""Legacy CredentialManager API (deprecated).

Prefer:
- `Brain.store_credential(...)`
- `Brain.get_credential(...)`

This file remains as a compatibility shim.
"""

from __future__ import annotations

import warnings

warnings.warn(
    "second_brain.credentials is legacy; use Brain.store_credential/get_credential",
    DeprecationWarning,
    stacklevel=2,
)

from .legacy.credentials import *  # noqa: F401,F403
