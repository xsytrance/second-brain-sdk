"""Second Brain — standalone, agent-friendly memory + credential vault."""
__version__ = "0.1.0"
__author__ = "Hermes Agent"
__email__ = "hermes@nousresearch.com"

# New generalized SQLite core
from .brain import Brain

# Legacy (encrypted JSON vault) API — kept for backwards compatibility.
# Importing these does not emit warnings unless the legacy API is used.
from .legacy.core import Vault, Event, Credential
from .legacy.session import Session
from .legacy.query import Query
from .legacy.credentials import CredentialManager

__all__ = [
    "Brain",
    "Vault",
    "Event",
    "Credential",
    "Session",
    "Query",
    "CredentialManager",
]
