from abc import ABC, abstractmethod
from typing import Any, Dict

class ToolResult(dict):
    """Standardized tool result.
    Keys: status, output, needs_approval, preview
    """
    pass

class BaseTool(ABC):
    name: str
    side_effects: bool = False

    @abstractmethod
    def run(self, arguments: Dict[str, Any], dry_run: bool = True) -> ToolResult:
        ...
