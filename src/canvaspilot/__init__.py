"""canvaspilot — Canvas LMS tools for agents (session or PAT)."""

from canvaspilot.api import CanvasAPI
from canvaspilot.client import CanvasAuthError, CanvasClient

__all__ = ["CanvasAPI", "CanvasAuthError", "CanvasClient"]
__version__ = "0.1.0"
