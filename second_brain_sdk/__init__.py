"""Second Brain SDK — Event-sourced knowledge base for AI agents."""
__version__ = "1.0.0"
__author__ = "Hermes Agent"
__email__ = "hermes@nousresearch.com"

from .core import Vault, Event, Credential
from .session import Session
from .query import Query
from .credentials import CredentialManager

__all__ = ["Vault", "Event", "Credential", "Session", "Query", "CredentialManager"]
