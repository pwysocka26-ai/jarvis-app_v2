from .client import MicrosoftGraphClient

class GraphMailService:
    def __init__(self, client: MicrosoftGraphClient):
        self.client = client

    def send_mail_app_only(self, user_id: str, subject: str, body_html: str, to_recipients: list[str]):
        """Send mail using /users/{id}/sendMail (app-only).
        Requires Mail.Send APPLICATION permission + admin consent.
        """
        url = f"https://graph.microsoft.com/v1.0/users/{user_id}/sendMail"
        payload = {
            "message": {
                "subject": subject,
                "body": {"contentType": "HTML", "content": body_html},
                "toRecipients": [{"emailAddress": {"address": a}} for a in to_recipients],
            },
            "saveToSentItems": "true",
        }
        return self.client.request("POST", url, json=payload)
