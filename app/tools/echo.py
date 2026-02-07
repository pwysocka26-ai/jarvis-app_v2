from __future__ import annotations
from typing import Dict, Any
from app.orchestrator.tools import Tool, ToolResult

class EchoTool(Tool):
    name = "echo"
    side_effects = False

    def run(self, args: Dict[str, Any], dry_run: bool = True) -> ToolResult:
        return ToolResult(ok=True, data={"echo": args, "dry_run": dry_run})
