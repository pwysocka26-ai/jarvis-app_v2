import uuid
from app.schemas import ActionPlan, ToolCall

def plan_from_text(text: str) -> ActionPlan:
    t = text.lower()

    # Minimal MVP planner — replace with LLM later.
    # Examples:
    if "wyślij" in t and "mail" in t:
        step = ToolCall(
            tool_name="graph.send_mail",
            arguments={
                "user_id": "me",  # in prod: map from Entra subject/UPN or configured mailbox
                "to": ["team@example.com"],
                "subject": "Update",
                "body_html": "<p>Draft…</p>",
            },
            dry_run=True,
            idempotency_key=str(uuid.uuid4()),
        )
        return ActionPlan(
            intent="send_email",
            steps=[step],
            summary="Prepare an email draft and request approval.",
            side_effects=True,
        )

    if "kalendarz" in t or "spotkan" in t:
        step = ToolCall(
            tool_name="graph.list_events",
            arguments={
                "user_id": "me",
                "start_iso": "2026-02-01T00:00:00",
                "end_iso": "2026-02-02T00:00:00",
            },
            dry_run=False,  # read-only
            idempotency_key=str(uuid.uuid4()),
        )
        return ActionPlan(
            intent="list_calendar_events",
            steps=[step],
            summary="List calendar events in a time window.",
            side_effects=False,
        )

    return ActionPlan(intent="qa", steps=[], summary="Answer user question (no tools).", side_effects=False)
