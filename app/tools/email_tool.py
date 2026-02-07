from .base import BaseTool, ToolResult

class EmailTool(BaseTool):
    name = "email.send"
    side_effects = True

    def run(self, arguments, dry_run=True) -> ToolResult:
        preview = {
            "to": arguments.get("to", []),
            "subject": arguments.get("subject", ""),
            "body": arguments.get("body", ""),
        }
        if dry_run:
            return ToolResult(status="ok", needs_approval=True, preview=preview, output={"message": "Draft ready"})
        # In real impl: send via Microsoft Graph (delegated/app-only) after approval
        return ToolResult(status="ok", needs_approval=False, preview=preview, output={"message": "Sent (stub)"})
