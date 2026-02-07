import os
import requests
import msal
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

class GraphAuthError(RuntimeError):
    pass

class GraphAPIError(RuntimeError):
    pass

def _build_msal_app():
    tenant_id = os.getenv("ENTRA_TENANT_ID", "")
    client_id = os.getenv("ENTRA_CLIENT_ID", "")
    client_secret = os.getenv("ENTRA_CLIENT_SECRET", "")
    if not (tenant_id and client_id and client_secret):
        raise GraphAuthError("Missing ENTRA_TENANT_ID / ENTRA_CLIENT_ID / ENTRA_CLIENT_SECRET")
    authority = f"https://login.microsoftonline.com/{tenant_id}"
    return msal.ConfidentialClientApplication(
        client_id=client_id,
        client_credential=client_secret,
        authority=authority,
    )

class MicrosoftGraphClient:
    """Microsoft Graph client using MSAL (client credentials / app-only).

    IMPORTANT:
    - Lazy initialization: Entra credentials are required only when Graph is actually used.
    - This keeps DEV/CI runnable without ENTRA_* set.
    """

    def __init__(self):
        self.scope = [os.getenv("GRAPH_SCOPE", "https://graph.microsoft.com/.default")]
        self._app = None
        self._session = requests.Session()

    def _ensure_app(self):
        if self._app is None:
            self._app = _build_msal_app()

    def get_token(self) -> str:
        self._ensure_app()
        result = self._app.acquire_token_silent(self.scope, account=None)
        if not result:
            result = self._app.acquire_token_for_client(scopes=self.scope)
        if "access_token" not in result:
            raise GraphAuthError(
                f"MSAL token error: {result.get('error')} {result.get('error_description')}"
            )
        return result["access_token"]

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.6, min=0.6, max=4.0),
        retry=retry_if_exception_type((requests.Timeout, requests.ConnectionError)),
    )
    def request(self, method: str, url: str, json=None, timeout: float = 30.0):
        token = self.get_token()
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        r = self._session.request(method, url, headers=headers, json=json, timeout=timeout)

        if r.status_code in (202, 204):
            return None
        if r.status_code >= 400:
            raise GraphAPIError(f"Graph API error: {r.status_code} {r.text}")
        return r.json()
