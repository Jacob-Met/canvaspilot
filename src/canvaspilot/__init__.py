"""canvaspilot — Canvas LMS MCP + API bundle (session broker or PAT)."""

from canvaspilot.api import CanvasAPI, assert_canvas_api_path, strip_html
from canvaspilot.bundle import CURATED_MCP_TOOLS, ESCAPE_HATCH_TOOLS, make_api, tool_inventory
from canvaspilot.client import CanvasAuthError, CanvasClient

__all__ = [
    "CURATED_MCP_TOOLS",
    "ESCAPE_HATCH_TOOLS",
    "CanvasAPI",
    "CanvasAuthError",
    "CanvasClient",
    "assert_canvas_api_path",
    "make_api",
    "strip_html",
    "tool_inventory",
]
__version__ = "0.1.1"
