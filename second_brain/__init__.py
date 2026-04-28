"""Second Brain — standalone, agent-friendly memory + credential vault."""
__version__ = "0.1.0"
__author__ = "Hermes Agent"
__email__ = "hermes@nousresearch.com"

from .core import Vault, Event, Credential
from .session import Session
from .query import Query
from .credentials import CredentialManager

__all__ = ["Vault", "Event", "Credential", "Session", "Query", "CredentialManager"]
