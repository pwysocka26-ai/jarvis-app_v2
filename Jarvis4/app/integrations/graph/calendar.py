from .client import MicrosoftGraphClient

class GraphCalendarService:
    def __init__(self, client: MicrosoftGraphClient):
        self.client = client

    def list_events(self, user_id: str, start_iso: str, end_iso: str):
        """List events via calendarView in a time window.
        Requires Calendars.Read APPLICATION permission + admin consent.
        """
        url = (
            f"https://graph.microsoft.com/v1.0/users/{user_id}/calendarView"
            f"?startDateTime={start_iso}&endDateTime={end_iso}"
        )
        return self.client.request("GET", url)

    def create_event(self, user_id: str, subject: str, start_iso: str, end_iso: str, timezone: str = "Europe/Warsaw"):
        """Create event.
        Requires Calendars.ReadWrite APPLICATION permission + admin consent.
        """
        url = f"https://graph.microsoft.com/v1.0/users/{user_id}/events"
        payload = {
            "subject": subject,
            "start": {"dateTime": start_iso, "timeZone": timezone},
            "end": {"dateTime": end_iso, "timeZone": timezone},
        }
        return self.client.request("POST", url, json=payload)
