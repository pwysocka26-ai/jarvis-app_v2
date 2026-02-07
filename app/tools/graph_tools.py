from app.tools.base import BaseTool, ToolResult
from app.integrations.graph.client import MicrosoftGraphClient
from app.integrations.graph.mail import GraphMailService
from app.integrations.graph.calendar import GraphCalendarService

class GraphSendMailTool(BaseTool):
    name = "graph.send_mail"
    side_effects = True

    def __init__(self):
        self._client = MicrosoftGraphClient()
        self._mail = GraphMailService(self._client)

    def run(self, arguments, dry_run=True) -> ToolResult:
        preview = {
            "user_id": arguments.get("user_id"),
            "to": arguments.get("to", []),
            "subject": arguments.get("subject", ""),
            "body_html": arguments.get("body_html", ""),
        }
        if dry_run:
            return ToolResult(status="ok", needs_approval=True, preview=preview, output={"message": "Graph mail preview ready"})
        self._mail.send_mail_app_only(
            user_id=preview["user_id"],
            subject=preview["subject"],
            body_html=preview["body_html"],
            to_recipients=preview["to"],
        )
        return ToolResult(status="ok", needs_approval=False, preview=preview, output={"message": "Mail sent via Graph"})

class GraphListEventsTool(BaseTool):
    name = "graph.list_events"
    side_effects = False

    def __init__(self):
        self._client = MicrosoftGraphClient()
        self._cal = GraphCalendarService(self._client)

    def run(self, arguments, dry_run=True) -> ToolResult:
        user_id = arguments["user_id"]
        start_iso = arguments["start_iso"]
        end_iso = arguments["end_iso"]
        data = self._cal.list_events(user_id=user_id, start_iso=start_iso, end_iso=end_iso)
        return ToolResult(status="ok", needs_approval=False, preview=None, output=data)
