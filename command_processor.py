# ============================================================
#  EmpowerAccess Desktop — core/command_processor.py
#  Orchestrates: intent → local tool OR Flask API → response
# ============================================================

import threading
import datetime
from typing import Callable

from core.intent_router import match_intent, get_label
from core.tool_executor import execute
from core.api_client    import APIClient


# ── Intents handled ENTIRELY locally (no Flask call needed) ──────────────────
LOCAL_ONLY_INTENTS = {
    "greeting", "time", "date",
    "vol_up", "vol_down", "mute", "vol_set",
    "shutdown", "restart", "sleep", "lock",
    "app_open", "app_close",
    "folder_open", "folder_create", "file_open", "file_create", "file_delete",
    "web_search", "open_url", "youtube",
    "screenshot", "timer", "reminder", "alarm",
    "clipboard_copy", "clipboard_paste",
    "joke", "logout", "exit",
}

# ── Intents that call Flask API endpoints ────────────────────────────────────
API_INTENTS = {"weather", "news", "stock", "sysinfo", "sos", "update"}

# ── Typo Mappings for Accuracy ──────────────────────────────────────────────
CITY_MAPPING = {
    # --- Major India Cities ---
    "bangalore": "Bengaluru", "banglore": "Bengaluru", "benguluru": "Bengaluru", 
    "bengalore": "Bengaluru", "benguluru": "Bengaluru", "banglore city": "Bengaluru",
    "bombay": "Mumbai", "mumbay": "Mumbai", "mumba": "Mumbai", "mumbari": "Mumbai", 
    "mombay": "Mumbai", "mumbai city": "Mumbai",
    "dilli": "Delhi", "dehli": "Delhi", "dehil": "Delhi", "dely": "Delhi", 
    "delhi ncr": "Delhi", "delhy": "Delhi",
    "hyderbad": "Hyderabad", "hydrabad": "Hyderabad", "hyderabaad": "Hyderabad", 
    "hyderabed": "Hyderabad", "hydrabad city": "Hyderabad",
    "madras": "Chennai", "chenai": "Chennai", "chennay": "Chennai", 
    "chenai city": "Chennai", "channai": "Chennai",
    "calcutta": "Kolkata", "kolkataa": "Kolkata", "kolkatta": "Kolkata", 
    "kalkata": "Kolkata", "kolkata city": "Kolkata",
    "punne": "Pune", "poona": "Pune", "puna": "Pune", "punee": "Pune", "pune city": "Pune",
    "jaipur": "Jaipur", "jaypur": "Jaipur", "jaipoor": "Jaipur", "pink city": "Jaipur",
    "lucknow": "Lucknow", "laknow": "Lucknow", "lakhnau": "Lucknow", "lakhnow": "Lucknow",
    "kanpur": "Kanpur", "kanpur city": "Kanpur", "caunpore": "Kanpur", "khanpur": "Kanpur",
    "nagpur": "Nagpur", "nagpure": "Nagpur", "nagpoor": "Nagpur",
    "indore": "Indore", "indor": "Indore", "endore": "Indore",
    "thane": "Thane", "tana": "Thane", "thance": "Thane",
    "bhopal": "Bhopal", "bopal": "Bhopal",
    "vizag": "Visakhapatnam", "visakhapatnam": "Visakhapatnam", "vishakapatnam": "Visakhapatnam", "visakha": "Visakhapatnam",
    "patna": "Patna", "paatna": "Patna", "patana": "Patna",
    "vadodara": "Vadodara", "baroda": "Vadodara", "vadodra": "Vadodara",
    "ghaziabad": "Ghaziabad", "gaziabad": "Ghaziabad", "ghaziyabad": "Ghaziabad",
    "ludhiana": "Ludhiana", "lhudiana": "Ludhiana", "ludhiyana": "Ludhiana",
    "agra": "Agra", "aggra": "Agra", "agara": "Agra",
    "ahemdabad": "Ahmedabad", "amedabad": "Ahmedabad", "ahmadabad": "Ahmedabad",
    "ahmadebad": "Ahmedabad", "amadabad": "Ahmedabad",
    "newyork": "New York", "ny": "New York", "nyc": "New York", "new york city": "New York",

    # --- Karnataka Cities ---
    "mysore": "Mysuru", "mysuru": "Mysuru", "misore": "Mysuru", "mysore city": "Mysuru",
    "hubli": "Hubballi", "hubballi": "Hubballi","obli":"Hubballi","ublee":"Hubballi", "hoobli": "Hubballi","huebe":"Hubballi", "huebe city":"Hubballi", "hubli city": "Hubballi",
    "dharwad": "Dharwad", "darwad": "Dharwad", "dharwad city": "Dharwad",
    "mangalore": "Mangaluru", "mangaluru": "Mangaluru", "manglore": "Mangaluru", "mangalore city": "Mangaluru",
    "belgaum": "Belagavi", "belagavi": "Belagavi", "belgavi": "Belagavi", "belgaum city": "Belagavi",
    "gulbarga": "Kalaburagi", "kalaburagi": "Kalaburagi", "kalburgi": "Kalaburagi", "gulbarga city": "Kalaburagi",
    "bellary": "Ballari", "ballari": "Ballari", "belary": "Ballari", "bellary city": "Ballari",
    "bijapur": "Vijayapura", "vijayapura": "Vijayapura", "vijapur": "Vijayapura", "bijapur city": "Vijayapura",
    "shimoga": "Shivamogga", "shivamogga": "Shivamogga", "shimoga city": "Shivamogga",
    "tumkur": "Tumakuru", "tumakuru": "Tumakuru", "tumakur": "Tumakuru", "tumkur city": "Tumakuru",
    "raichur": "Raichur", "richur": "Raichur", "raychur": "Raichur",
    "bidar": "Bidar", "beedar": "Bidar",
    "hassan": "Hassan", "hasan": "Hassan", "hassen": "Hassan",
    "udupi": "Udupi", "udapi": "Udupi", "odipi": "Udupi",
    "haveri":"haveri", "havre":"haveri", "haviery":"haveri", "havri":"haveri", "havari":"haveri", "haveri city":"haveri",
    "chitradurga":"Chitradurga","chitradurga":"Chitradurga","chitradurga":"Chitradurga","chitradurga":"Chitradurga","chitradurga":"Chitradurga","chitradurga":"Chitradurga",
    "davangere":"Davangere", "davanagere":"Davangere", "davanagere":"Davangere", "davanagere":"Davangere", "davanagere":"Davangere", "davanagere":"Davangere",
    "gadag":"Gadag","gadag":"Gadag","gadag":"Gadag","gadag":"Gadag","gadag":"Gadag","gadag":"Gadag",
    "gokak":"Gokak","gokak":"Gokak","gokak":"Gokak","gokak":"Gokak","gokak":"Gokak","gokak":"Gokak",
    "mandya":"Mandya", "mandyacity":"Mandya", "mandyacity":"Mandya", "mandyacity":"Mandya", "mandyacity":"Mandya", "mandyacity":"Mandya",
    "bagalkot":"Bagalkot","bagalkot":"Bagalkot","bagalkot":"Bagalkot","bagalkot":"Bagalkot","bagalkot":"Bagalkot","bagalkot":"Bagalkot",
    "chikmagalur": "Chikkamagaluru", "chikkamagaluru": "Chikkamagaluru", "chikmagalur city": "Chikkamagaluru"
}

STOCK_MAPPING = {
    "relience": "RELIANCE", "relyance": "RELIANCE", "relaince": "RELIANCE", 
    "relince": "RELIANCE", "reliance industries": "RELIANCE", "relianc": "RELIANCE",
    "tata consultancy": "TCS", "tata consultancy services": "TCS", "taccs": "TCS", 
    "tata": "TCS", "tc s": "TCS", "t s c": "TCS",
    "infosis": "INFY", "infisys": "INFY", "infy": "INFY", "infocys": "INFY", "infossys": "INFY",
    "apple": "AAPL", "aplle": "AAPL", "apel": "AAPL", "appleinc": "AAPL", "aple": "AAPL", "appel": "AAPL",
    "microsoft": "MSFT", "micosoft": "MSFT", "mcrosoft": "MSFT", "microsof": "MSFT", 
    "msoft": "MSFT", "micrasoft": "MSFT",
    "google": "GOOGL", "gogle": "GOOGL", "googal": "GOOGL", "alphabet": "GOOGL", 
    "googl": "GOOGL", "gooogle": "GOOGL",
    "tesla": "TSLA", "teslla": "TSLA", "telsa": "TSLA", "tesl": "TSLA", "tessla": "TSLA", "teslah": "TSLA",
    "amazon": "AMZN", "amzon": "AMZN", "amazan": "AMZN", "amazen": "AMZN", "amazone": "AMZN", "amzn": "AMZN"
}


# Decodes natural language commands separating offline tools and cloud assistants
class CommandProcessor:
    """
    Main orchestrator.  Call process(text, callback) — it's always async.
    callback(response: str, intent: str) is called on the result.
    """

    def __init__(self, api: APIClient):
        self.api = api
        self.user_name = "User"
        self.emergency_contact = ""
        self.user_city = ""

    def update_user_info(self, name: str, em_contact: str, city: str = ""):
        """Called by main app when profile is loaded."""
        self.user_name = name
        self.emergency_contact = em_contact
        self.user_city = city

    def process(self, text: str, callback: Callable[[str, str], None]):
        """
        Non-blocking.  Spins a thread so the GUI never freezes.
        """
        threading.Thread(
            target=self._process_sync,
            args=(text, callback),
            daemon=True
        ).start()

    def _process_sync(self, text: str, callback: Callable):
        # Safety try guard tracking runtime execution exceptions
        try:
            result  = match_intent(text)
            intent  = result.intent
            param   = result.param
            response = ""

            # ── 1. Local-only intents ──────────────────────────────────────
            if intent in LOCAL_ONLY_INTENTS:
                response = execute(intent, param, text)

            # ── 2. API intents ─────────────────────────────────────────────
            elif intent == "weather":
                # Extract city from command text or default to Bengaluru
                import re
                m = re.search(r"weather (?:in |of |for )?([a-zA-Z\s]+)", text.lower())
                city_raw = m.group(1).strip() if m else "Bengaluru"
                # Check for typos in city mapping
                city = CITY_MAPPING.get(city_raw.lower(), city_raw.title())
                res  = self.api.get_weather(city)
                if res.get("success"):
                    d = res["data"]
                    # Format for UI: WEATHER_DATA|city|temp|desc|hum|wind
                    response = f"WEATHER_DATA|{d['city']}|{d['temperature']}|{d['description']}|{d['humidity']}|{d['wind_speed']}"
                else:
                    response = f"Could not fetch weather: {res.get('message')}"

            elif intent == "news":
                cat = param or "technology"
                res = self.api.get_news(cat)
                if res.get("success") and res.get("articles"):
                    arts = res["articles"][:4]  # Show up to 4 headlines
                    
                    # Package as structured data for UI processing
                    # Format: NEWS_DATA|Category||Title|Source|URL||Title|Source|URL...
                    pkg = [f"NEWS_DATA|{cat.title()}"]
                    for a in arts:
                        # Clean pipe characters to prevent parsing errors
                        t = a['title'].replace("|", "-")
                        s = a['source'].replace("|", "-")
                        u = a['url']
                        pkg.append(f"{t}|{s}|{u}")
                    
                    response = "||".join(pkg)
                else:
                    response = f"Could not fetch news: {res.get('message')}"

            elif intent == "stock":
                import re
                # Blacklist common words so they aren't mistaken for stock symbols
                BLACKLIST = {"MARKET", "STOCK", "PRICE", "SHARE", "SHOW", "GET", "WHAT", "IS", "THE", "OF"}
                
                # First check for full company name/typo matches in the entire text
                symbol = None
                text_lower = text.lower()
                for typo, sym in STOCK_MAPPING.items():
                    if typo in text_lower:
                        symbol = sym
                        break
                
                if not symbol:
                    # Fallback to looking for 2-10 letter uppercase words
                    words = re.findall(r"\b([A-Z]{2,10})\b", text.upper())
                    for w in words:
                        if w not in BLACKLIST:
                            symbol = w
                            break
                
                # Fallback to RELIANCE if no specific symbol mentioned
                symbol = symbol or "RELIANCE"
                
                res = self.api.get_stock(symbol)
                if res.get("success"):
                    d = res["data"]
                    # Format for UI: STOCK_DATA|Name|Symbol|Price|Currency
                    response = f"STOCK_DATA|{d['company_name']}|{d['symbol']}|{d['price']}|{d['currency']}"
                else:
                    # Provide a more user-friendly error message
                    err = res.get("message", "Unknown error")
                    if "not found" in err.lower():
                        response = f"I couldn't find a stock with symbol '{symbol}'. Try saying 'get price of RELIANCE' or 'TCS stock'."
                    else:
                        response = f"Could not fetch stock: {err}"

            elif intent == "sysinfo":
                res = self.api.get_sysinfo()
                if res.get("success"):
                    d = res["data"]
                    # Format for UI: SYS_DATA|cpu_pct|ram_u|ram_t|ram_p|disk_u|disk_t|disk_p|bat|plug
                    bat  = d.get('battery') if d.get('battery') is not None else 'N'
                    plug = 1 if d.get('battery_plugged') else 0
                    response = (
                        f"SYS_DATA|{d['cpu_percent']}|{d['ram_used']}|{d['ram_total']}|{d['ram_percent']}|"
                        f"{d['disk_used']}|{d['disk_total']}|{d['disk_percent']}|{bat}|{plug}"
                    )
                else:
                    response = f"System info error: {res.get('message')}"

            elif intent == "sos":
                sos_location = self.user_city or "Current Location"
                res = self.api.trigger_sos(location=sos_location, contact=self.emergency_contact)
                if res.get("success"):
                    ts = datetime.datetime.now().strftime("%I:%M %p")
                    response = f"SOS_DATA|{sos_location}|{self.emergency_contact}|{ts}"
                else:
                    response = f"SOS failed: {res.get('message')}"

            elif intent == "update":
                res = self.api.check_version()
                if res.get("success"):
                    response = (
                        f"Latest version: {res['version']} "
                        f"(released {res['release_date']}). "
                        f"{res.get('description', '')}"
                    )
                else:
                    response = "Could not check for updates."

            # ── 3. LLM fallback → Flask /api/user/ai ──────────────────────
            elif intent == "llm_fallback":
                res = self.api.ask_ai(text)
                if res.get("success"):
                    response = res.get("response", "No response from AI.")
                else:
                    response = f"AI error: {res.get('message')}"

            else:
                response = f"I received your command: '{text}'. Processing."

            # ── Always log to Flask /api/user/command ──────────────────────
            # Fire-and-forget — we don't block on this
            threading.Thread(
                target=self.api.send_command,
                args=(text,),
                daemon=True
            ).start()

            callback(response, intent)

        # Recovers control silently from thread interruptions or database connection errors
        except Exception as e:
            callback(f"Processing error: {e}", "error")
