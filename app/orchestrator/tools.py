from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any

from app.config import settings

# Tool interface --------------------------------------------------------------

@dataclass
class ToolResult:
    ok: bool
    data: Dict[str, Any]

class ToolUnavailable(RuntimeError):
    pass

class Tool:
    name: str = "tool"
    side_effects: bool = False

    def run(self, args: Dict[str, Any], dry_run: bool = True) -> ToolResult:
        raise NotImplementedError

# Lazy registry ---------------------------------------------------------------

def get_tool(name: str) -> Tool:
    """Return a tool instance by name (lazy init).

    Important: do NOT initialize external integrations (e.g., Graph) at import time.
    This keeps DEV/CI runnable without credentials.
    """
    if name == "echo":
        from app.tools.echo import EchoTool
        return EchoTool()

    if name in ("graph_send_mail", "graph_calendar_create"):
        if not settings.graph_enabled:
            raise ToolUnavailable("Microsoft Graph integration is disabled (GRAPH_ENABLED=false)")
        # Import only when needed to avoid eager MSAL/Graph init
        from app.tools.graph_tools import GraphSendMailTool, GraphCalendarCreateEventTool
        if name == "graph_send_mail":
            return GraphSendMailTool()
        return GraphCalendarCreateEventTool()

    raise KeyError(f"Unknown tool: {name}")
