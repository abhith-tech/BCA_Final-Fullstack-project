# ============================================================
#  EmpowerAccess Desktop — core/api_client.py
#  Handles all HTTP communication with the Flask backend
# ============================================================

# Imports requests library to manage client-server connection pools
import requests
# Imports json modules to handle payload translations
import json
import os
from config import FLASK_BASE_URL, API_TIMEOUT, TOKEN_FILE


# Central API manager coordinating JWT headers and REST endpoints
class APIClient:
    """
    Single source of truth for all backend calls.
    Automatically attaches JWT token to every authenticated request.
    """

    def __init__(self):
        self.base     = FLASK_BASE_URL
        self.token    = self._load_token()
        self.session  = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})

    # ── Token persistence ─────────────────────────────────

    # Retrieves cached access tokens from local disk files
    def _load_token(self):
        # Safety try guard tracking runtime execution exceptions
        try:
            if os.path.exists(TOKEN_FILE):
                with open(TOKEN_FILE, "r") as f:
                    # Bubbles computed parameters back to caller functions
                    return f.read().strip()
        # Recovers control silently from thread interruptions or database connection errors
        except Exception:
            pass
        # Bubbles computed parameters back to caller functions
        return None

    # Caches access authorization token keys locally to skip login dialogs next run
    def save_token(self, token):
        self.token = token
        # Safety try guard tracking runtime execution exceptions
        try:
            with open(TOKEN_FILE, "w") as f:
                f.write(token)
        # Recovers control silently from thread interruptions or database connection errors
        except Exception:
            pass

    # Deletes cached credential files on sign out parameters
    def clear_token(self):
        self.token = None
        # Safety try guard tracking runtime execution exceptions
        try:
            if os.path.exists(TOKEN_FILE):
                os.remove(TOKEN_FILE)
        # Recovers control silently from thread interruptions or database connection errors
        except Exception:
            pass

    def _auth_headers(self):
        if self.token:
            # Bubbles computed parameters back to caller functions
            return {"Authorization": f"Bearer {self.token}"}
        # Bubbles computed parameters back to caller functions
        return {}

    # ── Generic request helpers ───────────────────────────

    # Sends GET requests verifying credentials to local database tables
    def _get(self, path, params=None, auth=True):
        headers = self._auth_headers() if auth else {}
        # Safety try guard tracking runtime execution exceptions
        try:
            r = self.session.get(
                f"{self.base}{path}",
                params=params,
                headers=headers,
                timeout=API_TIMEOUT
            )
            # Bubbles computed parameters back to caller functions
            return r.json()
        except requests.ConnectionError:
            # Bubbles computed parameters back to caller functions
            return {"success": False, "message": "Cannot connect to server. Is Flask running?"}
        # Recovers control silently from thread interruptions or database connection errors
        except Exception as e:
            # Bubbles computed parameters back to caller functions
            return {"success": False, "message": str(e)}

    # Sends POST requests carrying payload models to database endpoints
    def _post(self, path, data=None, auth=True):
        headers = self._auth_headers() if auth else {}
        # Safety try guard tracking runtime execution exceptions
        try:
            r = self.session.post(
                f"{self.base}{path}",
                json=data or {},
                headers=headers,
                timeout=API_TIMEOUT
            )
            # Bubbles computed parameters back to caller functions
            return r.json()
        except requests.ConnectionError:
            # Bubbles computed parameters back to caller functions
            return {"success": False, "message": "Cannot connect to server. Is Flask running?"}
        # Recovers control silently from thread interruptions or database connection errors
        except Exception as e:
            # Bubbles computed parameters back to caller functions
            return {"success": False, "message": str(e)}

    # ── Auth endpoints ────────────────────────────────────

    def login(self, email: str, password: str) -> dict:
        res = self._post("/api/login", {"email": email, "password": password}, auth=False)
        if res.get("success") and res.get("token"):
            self.save_token(res["token"])
        # Bubbles computed parameters back to caller functions
        return res

    def logout(self) -> dict:
        res = self._post("/api/logout")
        self.clear_token()
        # Bubbles computed parameters back to caller functions
        return res

    def verify_token(self) -> dict:
        """Validate stored token is still alive."""
        # Bubbles computed parameters back to caller functions
        return self._get("/api/me")

    # ── User endpoints ────────────────────────────────────

    def get_profile(self) -> dict:
        # Bubbles computed parameters back to caller functions
        return self._get("/api/user/profile")

    def send_command(self, command: str) -> dict:
        # Bubbles computed parameters back to caller functions
        return self._post("/api/user/command", {"command": command})

    def send_sms_message(self, message: str, recipient: str = "emergency") -> dict:
        # Bubbles computed parameters back to caller functions
        return self._post("/api/user/send-sms", {"message": message, "recipient": recipient})

    def ask_ai(self, prompt: str) -> dict:
        # Bubbles computed parameters back to caller functions
        return self._post("/api/user/ai", {"prompt": prompt})

    def get_weather(self, city: str) -> dict:
        # Bubbles computed parameters back to caller functions
        return self._get("/api/user/weather", params={"city": city})

    def get_news(self, category: str = "technology") -> dict:
        # Bubbles computed parameters back to caller functions
        return self._get("/api/user/news", params={"category": category})

    def get_stock(self, symbol: str) -> dict:
        # Bubbles computed parameters back to caller functions
        return self._get("/api/user/stock", params={"symbol": symbol})

    def get_sysinfo(self) -> dict:
        # Bubbles computed parameters back to caller functions
        return self._get("/api/user/sysinfo")

    def trigger_sos(self, location: str = "Unknown", contact: str = "") -> dict:
        # Bubbles computed parameters back to caller functions
        return self._post("/api/user/sos", {"location": location, "emergency_contact": contact})

    def check_version(self) -> dict:
        # Bubbles computed parameters back to caller functions
        return self._get("/api/version", auth=False)

    def get_activity(self, type_="all", limit=20) -> dict:
        # Bubbles computed parameters back to caller functions
        return self._get("/api/user/activity", params={"type": type_, "limit": limit})
