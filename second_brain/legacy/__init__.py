"""Legacy (encrypted JSON vault) API.

This module is retained for backwards compatibility while the project transitions
fully to the SQLite-backed `Brain` core.

New code should prefer:

    from second_brain import Brain

"""

from .core import Credential, Event, Vault
from .credentials import CredentialManager
from .query import Query
from .session import Session

__all__ = ["Vault", "Event", "Credential", "Query", "Session", "CredentialManager"]
