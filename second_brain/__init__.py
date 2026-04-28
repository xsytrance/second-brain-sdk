"""Second Brain — standalone, agent-friendly memory + credential vault."""
__version__ = "0.1.0"
__author__ = "Hermes Agent"
__email__ = "hermes@nousresearch.com"

# Legacy (encrypted JSON vault) API  kept for backwards compatibility
from .core import Vault, Event, Credential
from .session import Session
from .query import Query
from .credentials import CredentialManager

# New generalized SQLite core
from .brain import Brain

__all__ = [
    "Brain",
    "Vault",
    "Event",
    "Credential",
    "Session",
    "Query",
    "CredentialManager",
]
