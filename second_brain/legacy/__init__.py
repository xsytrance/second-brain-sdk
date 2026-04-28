"""Legacy (encrypted JSON vault) API.

This module is retained for backwards compatibility while the project transitions
fully to the SQLite-backed `Brain` core.

New code should prefer:

    from second_brain import Brain

"""

from .core import Vault, Event, Credential
from .query import Query
from .session import Session
from .credentials import CredentialManager

__all__ = ["Vault", "Event", "Credential", "Query", "Session", "CredentialManager"]
