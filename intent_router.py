# ============================================================
#  EmpowerAccess Desktop — core/intent_router.py
#  Two-tier hybrid intent engine:
#    Tier 1 → Rule-based (instant, no API cost)
#    Tier 2 → LLM fallback via Flask /api/user/ai
# ============================================================

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class IntentResult:
    intent:     str
    param:      Optional[str]
    confidence: float          # 1.0 = rule match, 0.0 = LLM fallback
    raw_text:   str


# ── Rule Table ────────────────────────────────────────────────────────────────
# Format:  keyword_pattern  →  (intent,  param_or_None)
# Patterns are matched against lowercased command text via substring or regex.

RULES = [
    # ── Greetings ──────────────────────────────────────
    (r"\b(hello|hi|hey|greet|good morning|good evening|helo|hallo|helloo|heyllo|hhello)\b",    "greeting",   None),

    # ── Time / Date ────────────────────────────────────
    (r"\b(time|tym|tim|tiime|timme|thime)\b",                                   "time",       None),
    (r"\b(date|dat|daet|ddate|daate|datee|today|todayy|tody|tday|todday|todey|day)\b", "date",       None),

    # ── Weather ────────────────────────────────────────
    (r"\b(weather|wether|weater|wheather|weathr|wather)\b",                     "weather",    None),
    (r"\b(temperature|temprature|temperator|tempature|tamperature)\b",          "weather",    None),
    (r"\b(rain|sunny|cloudy|forecast)\b",                                       "weather",    None),

    # ── News ───────────────────────────────────────────
    (r"\b(sports|business|health|science|entertainment) (news|newws|neews|nwes|nwews|newz)\b", "news", None),
    (r"\b(news|newws|neews|nwes|nwews|newz) (?:about|of|for|in)?\s+(sports|business|health|science|entertainment)\b", "news", None),
    (r"\btech(nology)? (news|newws|neews|nwes|nwews|newz)\b",                   "news",       "technology"),
    (r"\b(news|newws|neews|nwes|nwews|newz) (?:about|of|for|in)?\s+tech(nology)?\b", "news",       "technology"),
    (r"\b(news|newws|neews|nwes|nwews|newz)\b",                                 "news",       "technology"),
    (r"\b(headlines?|hedlines|headlins|heedlines|headlnes|hedlines)\b",         "news",       "technology"),

    # ── Stock ──────────────────────────────────────────
    (r"\b(stock|stok|stoc|stook|stck|stocks)\b",                                "stock",      None),
    (r"\bshare price\b",                                                        "stock",      None),
    (r"\b(market|mraket|markit|marcket|mrket|markat)\b",                        "stock",      None),

    # ── System Info ────────────────────────────────────
    (r"\b(cpu|cpo|cpi|cup|cpy|cgpu)\b",                                         "sysinfo",    "cpu"),
    (r"\b(ram|rm|raam|rem|rram|ramm)\b",                                        "sysinfo",    "ram"),
    (r"\b(memory|memry|memmory|memori|mamory|memore)\b",                        "sysinfo",    "ram"),
    (r"\b(battery|batery|battry|batary|bettery|battrery)\b",                    "sysinfo",    "battery"),
    (r"\b(disk|dsk|disc|dissk|diskk|deesk)\b",                                  "sysinfo",    "disk"),
    (r"\b(system|sistem|systm|systam|systen|sysytem) (info|status|stats)\b",    "sysinfo",    "all"),

    # ── Volume ─────────────────────────────────────────
    (r"\b(volume|volum|valume|volme|vulume|voluma) up\b",                       "vol_up",     None),
    (r"\b(volume|volum|valume|volme|vulume|voluma) down\b",                     "vol_down",   None),
    (r"\b(mute|mut|moot|mutt|myute|miute|unmute)\b",                            "mute",       None),
    (r"\b(volume|volum|valume|volme|vulume|voluma) (\d+)\b",                    "vol_set",    None),   # captures number in param

    # ── System Power ───────────────────────────────────
    (r"\b(shut down|shutdown|shutdwn|shtdown|shutdon|shutdoen|shotdown)\b",     "shutdown",   None),
    (r"\b(restart|restrt|resart|restert|reastart|restat)\b",                    "restart",    None),
    (r"\b(sleep|slep|sleap|sleeep|slpeep|sllep)\b",                             "sleep",      None),
    (r"\b(lock|lok|loc|lcok|llock|lockk) (screen|computer|pc)?\b",              "lock",       None),

    # ── Apps ───────────────────────────────────────────
    (r"\b(?:open|opn|oepn|opne|oppen|opin) (chrome|chrom|crome|chorome|chrrome|chorm|chrome.|chrome..)\b",         "app_open",   "chrome"),
    (r"\b(?:open|opn|oepn|opne|oppen|opin) (firefox|firfox|firefoks|firefoox|firfax|frefox|firefox.|firefox..)\b",   "app_open",   "firefox"),
    (r"\b(?:open|opn|oepn|opne|oppen|opin) (notepad|notpad|nodepad|noteopad|noetpad|ntepad|notepad.|notepad..)\b",   "app_open",   "notepad"),
    (r"\b(?:open|opn|oepn|opne|oppen|opin) (calc(?:ulator)?|calulator|caculator|calculater|calculeter|calcualtor|calc.|calc..)\b", "app_open", "calculator"),
    (r"\b(?:open|opn|oepn|opne|oppen|opin) (settings|setings|seting|settngs|settins|setting|settings.|settings..)\b",  "app_open",   "settings"),
    (r"\b(?:open|opn|oepn|opne|oppen|opin) (vs ?code|visual studio code|viscude|visual studeo|vscde|vs codee|vs..)\b", "app_open", "vscode"),
    (r"\b(?:open|opn|oepn|opne|oppen|opin) (file explorer|fil explorer|file exploer|file xplorer|file explorr|fiel explorer|file explorer.|file explorer..)\b", "app_open", "file explorer"),
    (r"\b(?:open|opn|oepn|opne|oppen|opin) (task ?manager|tas manager|task manger|tsk manager|task managar|task maneger|task manager.|task manager..)\b", "app_open", "task manager"),
    (r"\b(?:open|opn|oepn|opne|oppen|opin) (paint|pait|pant|pianit|pyant|paintt|paint.|paint..)\b",              "app_open",   "mspaint"),
    (r"\b(?:open|opn|oepn|opne|oppen|opin) (msword|ms word|word|wrd|wored|wrod|worrd|wuord|msword.|msword..)\b",   "app_open",   "msword"),
    (r"\b(?:open|opn|oepn|opne|oppen|opin) (ms excel|msexcel|excel|exel|xcel|excall|exell|axcel|ms excel.|ms excel..)\b", "app_open", "ms excel"),
    (r"\b(?:open|opn|oepn|opne|oppen|opin) (spotify|spotfy|spottify|sptify|spotifi|spatify|spotify.|spotify..)\b",   "app_open",   "spotify"),
    (r"\b(?:open|opn|oepn|opne|oppen|opin) (telegram|telegran|telgram|tellegram|telegrm|teleigram|telegram.|telegram..)\b", "app_open", "telegram"),
    (r"\b(?:open|opn|oepn|opne|oppen|opin) (whatsapp|watsapp|whatsap|whtsapp|whatapp|whatsappp|whatsapp.|whatsapp..)\b", "app_open", "whatsapp"),
    (r"\b(?:open|opn|oepn|opne|oppen|opin) (calendar|calender|calandar|calendr|clendar|calander|calendar.|calendar..)\b", "app_open", "calendar"),
    (r"\b(?:open|opn|oepn|opne|oppen|opin) google (calendar|calender|calandar|calendr|clendar|calander)\b", "app_open", "google calendar"),
    (r"\b(?:open|opn|oepn|opne|oppen|opin) (photos|fotos|photoes|phoots|phots|potos|photos.|photos..)\b",          "app_open",   "photos"),
    (r"\b(?:close|clos|clse|clsoe|cloose|clouse) (chrome|chrom|crome|chorome|chrrome|chorm|chrome\.|chrome\.\.)\b",         "app_close",   "chrome"),
    (r"\b(?:close|clos|clse|clsoe|cloose|clouse) (firefox|firfox|firefoks|firefoox|firfax|frefox|firefox\.|firefox\.\.)\b",   "app_close",   "firefox"),
    (r"\b(?:close|clos|clse|clsoe|cloose|clouse) (notepad|notpad|nodepad|noteopad|noetpad|ntepad|notepad\.|notepad\.\.)\b",   "app_close",   "notepad"),
    (r"\b(?:close|clos|clse|clsoe|cloose|clouse) (calc(?:ulator)?|calulator|caculator|calculater|calculeter|calcualtor|calc\.|calc\.\.)\b", "app_close", "calculator"),
    (r"\b(?:close|clos|clse|clsoe|cloose|clouse) (settings|setings|seting|settngs|settins|setting|settings\.|settings\.\.)\b",  "app_close",   "settings"),
    (r"\b(?:close|clos|clse|clsoe|cloose|clouse) (vs ?code|visual studio code|viscude|visual studeo|vscde|vs codee|vs\.\.)\b", "app_close", "vscode"),
    (r"\b(?:close|clos|clse|clsoe|cloose|clouse) (file explorer|fil explorer|file exploer|file xplorer|file explorr|fiel explorer|file explorer\.|file explorer\.\.)\b", "app_close", "file explorer"),
    (r"\b(?:close|clos|clse|clsoe|cloose|clouse) (task ?manager|tas manager|task manger|tsk manager|task managar|task maneger|task manager\.|task manager\.\.)\b", "app_close", "task manager"),
    (r"\b(?:close|clos|clse|clsoe|cloose|clouse) (paint|pait|pant|pianit|pyant|paintt|paint\.|paint\.\.)\b",              "app_close",   "mspaint"),
    (r"\b(?:close|clos|clse|clsoe|cloose|clouse) (msword|ms word|word|wrd|wored|wrod|worrd|wuord|msword\.|msword\.\.)\b",   "app_close",   "msword"),
    (r"\b(?:close|clos|clse|clsoe|cloose|clouse) (ms excel|msexcel|excel|exel|xcel|excall|exell|axcel|ms excel\.|ms excel\.\.)\b", "app_close", "ms excel"),
    (r"\b(?:close|clos|clse|clsoe|cloose|clouse) (spotify|spotfy|spottify|sptify|spotifi|spatify|spotify\.|spotify\.\.)\b",   "app_close",   "spotify"),
    (r"\b(?:close|clos|clse|clsoe|cloose|clouse) (telegram|telegran|telgram|tellegram|telegrm|teleigram|telegram\.|telegram\.\.)\b", "app_close", "telegram"),
    (r"\b(?:close|clos|clse|clsoe|cloose|clouse) (whatsapp|watsapp|whatsap|whtsapp|whatapp|whatsappp|whatsapp\.|whatsapp\.\.)\b", "app_close", "whatsapp"),
    (r"\b(?:close|clos|clse|clsoe|cloose|clouse) (calendar|calender|calandar|calendr|clendar|calander|calendar\.|calendar\.\.)\b", "app_close", "calendar"),
    (r"\b(?:close|clos|clse|clsoe|cloose|clouse) google (calendar|calender|calandar|calendr|clendar|calander)\b", "app_close", "google calendar"),
    (r"\b(?:close|clos|clse|clsoe|cloose|clouse) (photos|fotos|photoes|phoots|phots|potos|photos\.|photos\.\.)\b",          "app_close",   "photos"),
    (r"\b(?:close|clos|clse|clsoe|cloose|clouse) (.+)",                                           "app_close",  None),

    # ── Files / Folders ────────────────────────────────
    (r"\b(?:open|opn|oepn|opne|oppen|opin) (my )?(downloads|documents|desktop|pictures|music|videos)\b",  "folder_open", None),
    (r"\b(?:open|opn|oepn|opne|oppen|opin) (folder|foldr|follder|flder|foolder|foualder)\b",      "folder_open", None),
    (r"\b(?:open|opn|oepn|opne|oppen|opin) (file|fil|fiil|flle|fille|faile)\b",                   "file_open",   None),
    (r"\b(?:create|creat|crate|creaat|creeate|craete) (folder|foldr|follder|flder|foolder|foualder)\b", "folder_create", None),
    (r"\b(?:create|creat|crate|creaat|creeate|craete) (file|fil|fiil|flle|fille|faile)\b",        "file_create",   None),
    (r"\b(?:delete|delet|delte|dlete|dolete|delate) (file|fil|fiil|flle|fille|faile)\b",          "file_delete",   None),

    # ── Browser / Internet ─────────────────────────────
    (r"\b(?:search|serch|saerch|sarch|srch|searh) (?:for |about |online )?(.+)",                  "web_search",  None),
    (r"\b(?:open|opn|oepn|opne|oppen|opin) (https?://\S+|www\.\S+)",                              "open_url",    None),
    (r"\b(?:google|googel|gogle|googol|goolge|gooogle) (.+)",                                     "web_search",  None),
    (r"\b(?:(?:open|opn|oepn|opne|oppen|opin) )?(youtube|youtub|you tube|yotube|uutube|yuotube)(?:\s+(.+))?", "youtube", None),

    # ── Screenshot ─────────────────────────────────────
    (r"\b(take |capture )?(screenshot|screnshot|screensot|screenshoot|scrunshot|scrnshot)\b",     "screenshot",  None),

    # ── Reminder / Timer ───────────────────────────────
    (r"\bset (a )?(timer|timr|timmer|tiimer|tmer|tymer)\b",                     "timer",       None),
    (r"\b(remind|remnd|remin|remid|ramind|remine) me\b",                        "reminder",    None),
    (r"\b(alarm|alrm|alaram|allarm|alaarm|alram)\b",                            "alarm",       None),

    # ── Clipboard ──────────────────────────────────────
    (r"\b(copy|copi|cpy|copiy|cppy|coopy)\b",                                   "clipboard_copy",  None),
    (r"\b(paste|past|paest|paset|pste|paaste)\b",                               "clipboard_paste", None),

    # ── SOS ────────────────────────────────────────────
    (r"\b(sos|soos|soss|emergency|emrgency|emergncy|amargancy|imergency|emergensy|help me|send help)\b", "sos", None),

    # ── Updates ────────────────────────────────────────
    (r"\b(check update|update software|new version|software version|update|updat|uopdate|udpate|updete)\b", "update", None),

    # ── Jokes / Fun ────────────────────────────────────
    (r"\b(tell me a joke|joke|jok|joek|jooke|djoke|jock)\b",                    "joke",        None),

    # ── Exit / Logout ──────────────────────────────────
    (r"\b(logout|log out|sign out|logut|loguot|lgout|logeout|loggout)\b",       "logout",      None),
    (r"\b(exit|close app|quit|exitt|exet|ixit|xit|exxix)\b",                    "exit",        None),
]


# Runs custom regex classifications to route speech commands
def match_intent(text: str) -> IntentResult:
    """
    Returns an IntentResult.
    Confidence 1.0  → rule matched, execute locally.
    Confidence 0.0  → send to Flask /api/user/ai for LLM handling.
    """
    lower = text.lower().strip()

    for pattern, intent, param in RULES:
        m = re.search(pattern, lower)
        if m:
            # For patterns that capture a group (e.g. volume 50, close chrome)
            resolved_param = param
            if param is None and m.lastindex:
                resolved_param = m.group(m.lastindex).strip()

            # Bubbles computed parameters back to caller functions
            return IntentResult(
                intent=intent,
                param=resolved_param,
                confidence=1.0,
                raw_text=text
            )

    # No rule matched → LLM fallback
    # Bubbles computed parameters back to caller functions
    return IntentResult(
        intent="llm_fallback",
        param=None,
        confidence=0.0,
        raw_text=text
    )


# ── Human-readable intent labels (for display in chat) ───────────────────────

INTENT_LABELS = {
    "greeting":       "Greeting",
    "time":           "Current Time",
    "date":           "Current Date",
    "weather":        "Weather",
    "news":           "News",
    "stock":          "Stock Price",
    "sysinfo":        "System Info",
    "vol_up":         "Volume Up",
    "vol_down":       "Volume Down",
    "mute":           "Mute / Unmute",
    "vol_set":        "Set Volume",
    "shutdown":       "Shutdown PC",
    "restart":        "Restart PC",
    "sleep":          "Sleep PC",
    "lock":           "Lock Screen",
    "app_open":       "Open App",
    "app_close":      "Close App",
    "folder_open":    "Open Folder",
    "folder_create":  "Create Folder",
    "file_open":      "Open File",
    "file_create":    "Create File",
    "file_delete":    "Delete File",
    "web_search":     "Web Search",
    "open_url":       "Open Website",
    "youtube":        "YouTube Search",
    "screenshot":     "Screenshot",
    "timer":          "Set Timer",
    "reminder":       "Set Reminder",
    "alarm":          "Set Alarm",
    "clipboard_copy": "Copy",
    "clipboard_paste":"Paste",
    "sos":            "Emergency SOS",
    "update":         "Check Update",
    "joke":           "Joke",
    "logout":         "Logout",
    "exit":           "Exit App",
    "llm_fallback":   "AI Assistant",
}

def get_label(intent: str) -> str:
    # Bubbles computed parameters back to caller functions
    return INTENT_LABELS.get(intent, intent.replace("_", " ").title())
