# ============================================================
#  EmpowerAccess Desktop — core/tool_executor.py
#  Executes local system actions triggered by intent router
# ============================================================

import os
import sys
import subprocess
import datetime
import threading
import webbrowser
import urllib.parse
import ctypes
import platform
import time
import re

_NOTIFICATION_CALLBACK = None

def set_notification_callback(cb):
    global _NOTIFICATION_CALLBACK
    _NOTIFICATION_CALLBACK = cb

def _parse_num(text):
    """Converts words like 'one', 'two' to digits."""
    mapping = {
        "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
        "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
        "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
        "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60
    }
    text = text.strip().lower()
    if text.isdigit():
        # Bubbles computed parameters back to caller functions
        return int(text)
    # Bubbles computed parameters back to caller functions
    return mapping.get(text, 0)

# Safety try guard tracking runtime execution exceptions
try:
    import pyautogui
    HAS_PYAUTOGUI = True
except ImportError:
    HAS_PYAUTOGUI = False

# Safety try guard tracking runtime execution exceptions
try:
    import pyperclip
    HAS_CLIPBOARD = True
except ImportError:
    HAS_CLIPBOARD = False


IS_WINDOWS = platform.system() == "Windows"


# ── App path registry ─────────────────────────────────────────────────────────

APP_PATHS = {
    "chrome":    [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ],
    "firefox":   [r"C:\Program Files\Mozilla Firefox\firefox.exe"],
    "notepad":   "notepad.exe",
    "calculator": "calc.exe",
    "settings":  "ms-settings:",
    "explorer":  "explorer.exe",
    "file explorer": "explorer.exe",
    "task manager": "taskmgr.exe",
    "mspaint":   "mspaint.exe",
    "msword":    "winword.exe",
    "ms excel":  "excel.exe",
    "photos":    "ms-photos:",
    "vscode":    [
        r"C:\Users\{user}\AppData\Local\Programs\Microsoft VS Code\Code.exe".format(
            user=os.environ.get("USERNAME", "")
        ),
        "code",
    ],
    "spotify":   [
        r"C:\Users\{user}\AppData\Roaming\Spotify\Spotify.exe".format(
            user=os.environ.get("USERNAME", "")
        ),
        "spotify.exe"
    ],
    "telegram":  [
        r"C:\Users\{user}\AppData\Roaming\Telegram Desktop\Telegram.exe".format(
            user=os.environ.get("USERNAME", "")
        ),
        "telegram.exe"
    ],
    "whatsapp":  ["whatsapp.exe", "WhatsApp"],
}

FOLDER_PATHS = {
    "downloads":  os.path.join(os.path.expanduser("~"), "Downloads"),
    "documents":  os.path.join(os.path.expanduser("~"), "Documents"),
    "desktop":    os.path.join(os.path.expanduser("~"), "Desktop"),
    "pictures":   os.path.join(os.path.expanduser("~"), "Pictures"),
    "music":      os.path.join(os.path.expanduser("~"), "Music"),
    "videos":     os.path.join(os.path.expanduser("~"), "Videos"),
}

# ── Nircmd path (optional, for audio control on Windows) ─────────────────────
NIRCMD = os.path.join(os.path.dirname(__file__), "..", "assets", "nircmd.exe")


# ── Main executor ─────────────────────────────────────────────────────────────

# Main executor mapping parsed variables to local systems
def execute(intent: str, param: str | None, raw_text: str) -> str:
    """
    Dispatches intent to the correct handler.
    Returns a human-readable response string.
    """
    # Safety try guard tracking runtime execution exceptions
    try:
        fn = _DISPATCH.get(intent)
        if fn:
            # Bubbles computed parameters back to caller functions
            return fn(param, raw_text)
        # Bubbles computed parameters back to caller functions
        return f"Intent '{intent}' has no local handler."
    # Recovers control silently from thread interruptions or database connection errors
    except Exception as e:
        # Bubbles computed parameters back to caller functions
        return f"Execution error: {e}"


# ── Individual handlers ───────────────────────────────────────────────────────

def _greeting(param, raw):
    hour = datetime.datetime.now().hour
    if hour < 12:
        # Bubbles computed parameters back to caller functions
        return "Good morning!iam ready to assist you."
    elif hour < 17:
        # Bubbles computed parameters back to caller functions
        return "Good afternoon! How can I help you today?"
    else:
        # Bubbles computed parameters back to caller functions
        return "Good evening! What can I do for you?"

def _time(param, raw):
    now = datetime.datetime.now().strftime("%I:%M %p")
    # Bubbles computed parameters back to caller functions
    return f"The current time is {now}."

def _date(param, raw):
    today = datetime.datetime.now().strftime("%A, %d %B %Y")
    # Bubbles computed parameters back to caller functions
    return f"Today is {today}."

def _app_open(param, raw):
    if not param:
        # Bubbles computed parameters back to caller functions
        return "Which application should I open?"
    
    param_lower = param.lower().strip()
    
    # Specific web fallbacks
    web_fallback_map = {
        "telegram": "https://web.telegram.org",
        "whatsapp": "https://web.whatsapp.com",
        "spotify": "https://open.spotify.com",
        "google calendar": "https://calendar.google.com",
        "calendar": "https://calendar.google.com",
        "calender": "https://calendar.google.com",
        "youtube": "https://www.youtube.com"
    }

    paths = APP_PATHS.get(param_lower)
    if isinstance(paths, str):
        paths = [paths]
    
    if paths:
        for p in paths:
            # Safety try guard tracking runtime execution exceptions
            try:
                if os.path.exists(p) or p.endswith(":"):
                    os.startfile(p)
                    # Bubbles computed parameters back to caller functions
                    return f"Opening {param_lower}."
                else:
                    # Check if subprocess works
                    ret = subprocess.call(["cmd", "/c", "start", "", p], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    if ret == 0:
                        # Bubbles computed parameters back to caller functions
                        return f"Opening {param_lower}."
            # Recovers control silently from thread interruptions or database connection errors
            except Exception:
                continue
                
    # Fallback to WEB version if applicable
    if param_lower in web_fallback_map:
        webbrowser.open(web_fallback_map[param_lower])
        # Bubbles computed parameters back to caller functions
        return f"App not found locally. Opening {param_lower} in web browser."
        
    # Generic fallback
    # Safety try guard tracking runtime execution exceptions
    try:
        subprocess.Popen([param_lower], shell=True)
        # Bubbles computed parameters back to caller functions
        return f"Attempting to open {param_lower}."
    # Recovers control silently from thread interruptions or database connection errors
    except Exception as e:
        # Bubbles computed parameters back to caller functions
        return f"Could not open {param_lower}: {e}"

def _app_close(param, raw):
    if not param:
        # Bubbles computed parameters back to caller functions
        return "Which app should I close?"
    
    param_lower = param.lower().strip()
    
    # Strip common prefix/suffix from voice commands (e.g., "the chrome app" -> "chrome")
    import re
    param_lower = re.sub(r'^the\s+', '', param_lower)
    param_lower = re.sub(r'\s+(app|application|program)$', '', param_lower)
    param_lower = param_lower.strip(' .,!?')
    
    # Prevent closing Task Manager at user request
    if param_lower in ["task manager", "taskmanager", "task maneger", "taskmaneger"]:
        # Bubbles computed parameters back to caller functions
        return "Closing Task Manager is disabled.you should do it manually"
    
    # Map common spoken names to their actual executables (list of possible names)
    app_exe_map = {
        "chrome": ["chrome.exe"],
        "firefox": ["firefox.exe"],
        "notepad": ["notepad.exe"],
        "calculator": ["CalculatorApp.exe", "calc.exe"],
        "calc": ["CalculatorApp.exe", "calc.exe"],
        "settings": ["SystemSettings.exe"],
        "photos": ["Microsoft.Photos.exe", "PhotosApp.exe", "Photos.exe"],
        "vs code": ["code.exe"],
        "vscode": ["code.exe"],
        "visual studio code": ["code.exe"],
        "file explorer": ["explorer.exe"],
        "explorer": ["explorer.exe"],
        "paint": ["mspaint.exe", "PaintApp.exe"],
        "word": ["winword.exe"],
        "msword": ["winword.exe"],
        "ms word": ["winword.exe"],
        "excel": ["excel.exe"],
        "ms excel": ["excel.exe"],
        "msexcel": ["excel.exe"],
        "spotify": ["Spotify.exe"],
        "telegram": ["Telegram.exe"],
        "whatsapp": ["WhatsApp.exe"],
        "google calendar": ["chrome.exe"] # usually a web app, let window match handle it
    }

    exe_names = app_exe_map.get(param_lower, [f"{param_lower}.exe"])

    # Safety try guard tracking runtime execution exceptions
    try:
        if IS_WINDOWS:
            if param_lower in ["file explorer", "explorer"]:
                # Gracefully close File Explorer windows without killing the Windows Shell
                ps_cmd = '(New-Object -comObject Shell.Application).Windows() | ForEach-Object { $_.Quit() }'
                subprocess.call(["powershell", "-Command", ps_cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                # For web apps / PWAs or unsupported names, use window title matching fallback
                window_match_apps = ["youtube", "you tube", "google calendar", "google calender", "calendar", "calender", "telegram", "whatsapp", "spotify", "photos"]
                if param_lower in window_match_apps:
                    subprocess.call(["taskkill", "/f", "/fi", f"WINDOWTITLE eq *{param}*"],
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                for exe_name in exe_names:
                    subprocess.call(["taskkill", "/f", "/im", exe_name],
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        # Bubbles computed parameters back to caller functions
        return f"Closing {param_lower}."
    # Recovers control silently from thread interruptions or database connection errors
    except Exception as e:
        # Bubbles computed parameters back to caller functions
        return f"Could not close {param_lower}: {e}"

def _folder_open(param, raw):
    # Try to find known folder keyword in raw text
    lower = raw.lower()
    for key, path in FOLDER_PATHS.items():
        if key in lower:
            if os.path.exists(path):
                os.startfile(path)
                # Bubbles computed parameters back to caller functions
                return f"Opening {key} folder."
    # Fallback: open File Explorer
    os.startfile(os.path.expanduser("~"))
    # Bubbles computed parameters back to caller functions
    return "Opening your home folder."

def _file_open(param, raw):
    import re
    m = re.search(r"(?:open|opn|oepn|opne|oppen|opin) (?:file|fil|fiil|flle|fille|faile) (.+)", raw.lower())
    name = m.group(1).strip() if m else None
    if not name:
        # Bubbles computed parameters back to caller functions
        return "Which file should I open?"
    
    path = os.path.join(os.path.expanduser("~"), "Downloads", name)
    if os.path.exists(path) and os.path.isfile(path):
        # Safety try guard tracking runtime execution exceptions
        try:
            os.startfile(path)
            # Bubbles computed parameters back to caller functions
            return f"Opening file '{name}'."
        # Recovers control silently from thread interruptions or database connection errors
        except Exception as e:
            # Bubbles computed parameters back to caller functions
            return f"Failed to open file: {e}"
    
    # Extension fallback
    if "." not in name:
        path_txt = path + ".txt"
        if os.path.exists(path_txt) and os.path.isfile(path_txt):
            # Safety try guard tracking runtime execution exceptions
            try:
                os.startfile(path_txt)
                # Bubbles computed parameters back to caller functions
                return f"Opening file '{name}.txt'."
            # Recovers control silently from thread interruptions or database connection errors
            except Exception as e:
                # Bubbles computed parameters back to caller functions
                return f"Failed to open file: {e}"

    # Bubbles computed parameters back to caller functions
    return f"File '{name}' not found in Downloads."

def _folder_create(param, raw):
    # Extract folder name from raw text
    import re
    m = re.search(r"(?:create|creat|crate|creaat|creeate|craete) (?:folder|foldr|follder|flder|foolder|foualder) (.+)", raw.lower())
    name = m.group(1).strip() if m else "New Folder"
    path = os.path.join(os.path.expanduser("~"), "Downloads", name)
    os.makedirs(path, exist_ok=True)
    # Bubbles computed parameters back to caller functions
    return f"Created folder '{name}' on your Downloads."

def _file_create(param, raw):
    import re
    m = re.search(r"(?:create|creat|crate|creaat|creeate|craete) (?:file|fil|fiil|flle|fille|faile) (.+)", raw.lower())
    name = m.group(1).strip() if m else "New File.txt"
    if "." not in name:
        name += ".txt"
    path = os.path.join(os.path.expanduser("~"), "Downloads", name)
    # Safety try guard tracking runtime execution exceptions
    try:
        with open(path, "w") as f:
            f.write("")
        # Bubbles computed parameters back to caller functions
        return f"Created file '{name}' on your Downloads."
    # Recovers control silently from thread interruptions or database connection errors
    except Exception as e:
        # Bubbles computed parameters back to caller functions
        return f"Failed to create file: {e}"

def _file_delete(param, raw):
    import re
    m = re.search(r"(?:delete|delet|delte|dlete|dolete|delate) (?:file|fil|fiil|flle|fille|faile) (.+)", raw.lower())
    name = m.group(1).strip() if m else None
    if not name:
        # Bubbles computed parameters back to caller functions
        return "Which file should I delete?"
    
    path = os.path.join(os.path.expanduser("~"), "Downloads", name)
    
    if os.path.exists(path) and os.path.isfile(path):
        # Safety try guard tracking runtime execution exceptions
        try:
            os.remove(path)
            # Bubbles computed parameters back to caller functions
            return f"Deleted file '{name}' from Downloads."
        # Recovers control silently from thread interruptions or database connection errors
        except Exception as e:
            # Bubbles computed parameters back to caller functions
            return f"Failed to delete file: {e}"
    
    # Try with .txt extension fallback
    if "." not in name:
        path_txt = path + ".txt"
        if os.path.exists(path_txt) and os.path.isfile(path_txt):
            # Safety try guard tracking runtime execution exceptions
            try:
                os.remove(path_txt)
                # Bubbles computed parameters back to caller functions
                return f"Deleted file '{name}.txt' from Downloads."
            # Recovers control silently from thread interruptions or database connection errors
            except Exception as e:
                # Bubbles computed parameters back to caller functions
                return f"Failed to delete file: {e}"
            
    # Bubbles computed parameters back to caller functions
    return f"File '{name}' not found in Downloads."

def _vol_up(param, raw):
    if IS_WINDOWS and os.path.exists(NIRCMD):
        subprocess.call([NIRCMD, "changesysvolume", "5000"])
        # Bubbles computed parameters back to caller functions
        return "Volume increased."
    elif HAS_PYAUTOGUI:
        pyautogui.press("volumeup")
        # Bubbles computed parameters back to caller functions
        return "Volume increased."
    # Bubbles computed parameters back to caller functions
    return "Volume control not available."

def _vol_down(param, raw):
    if IS_WINDOWS and os.path.exists(NIRCMD):
        subprocess.call([NIRCMD, "changesysvolume", "-5000"])
        # Bubbles computed parameters back to caller functions
        return "Volume decreased."
    elif HAS_PYAUTOGUI:
        pyautogui.press("volumedown")
        # Bubbles computed parameters back to caller functions
        return "Volume decreased."
    # Bubbles computed parameters back to caller functions
    return "Volume control not available."

def _mute(param, raw):
    if IS_WINDOWS and os.path.exists(NIRCMD):
        subprocess.call([NIRCMD, "mutesysvolume", "2"])
        # Bubbles computed parameters back to caller functions
        return "Volume toggled."
    elif HAS_PYAUTOGUI:
        pyautogui.press("volumemute")
        # Bubbles computed parameters back to caller functions
        return "Volume muted/unmuted."
    # Bubbles computed parameters back to caller functions
    return "Mute control not available."

def _vol_set(param, raw):
    import re
    m = re.search(r"\d+", raw)
    level = int(m.group()) if m else 50
    level = max(0, min(100, level))
    if IS_WINDOWS and os.path.exists(NIRCMD):
        vol = int(65535 * level / 100)
        subprocess.call([NIRCMD, "setsysvolume", str(vol)])
        # Bubbles computed parameters back to caller functions
        return f"Volume set to {level}%."
    # Bubbles computed parameters back to caller functions
    return f"Requested volume {level}% — NirCmd not found."

def _shutdown(param, raw):
    if IS_WINDOWS:
        os.system("shutdown /s /t 10")
        # Bubbles computed parameters back to caller functions
        return "System will shut down in 10 seconds. Type 'shutdown /a' to cancel."
    else:
        os.system("shutdown -h +1")
        # Bubbles computed parameters back to caller functions
        return "Shutdown scheduled in 1 minute."

def _restart(param, raw):
    if IS_WINDOWS:
        os.system("shutdown /r /t 10")
        # Bubbles computed parameters back to caller functions
        return "System will restart in 10 seconds."
    else:
        os.system("shutdown -r +1")
        # Bubbles computed parameters back to caller functions
        return "Restart scheduled."

def _sleep(param, raw):
    if IS_WINDOWS:
        os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
        # Bubbles computed parameters back to caller functions
        return "Putting system to sleep."
    # Bubbles computed parameters back to caller functions
    return "Sleep command sent."

def _lock(param, raw):
    if IS_WINDOWS:
        ctypes.windll.user32.LockWorkStation()
        # Bubbles computed parameters back to caller functions
        return "Screen locked."
    # Bubbles computed parameters back to caller functions
    return "Lock command sent."

def _web_search(param, raw):
    import re
    # Extract search query — regex has ONE capture group, so use group(1)
    m = re.search(r"(?:(?:search|serch|saerch|sarch|srch|searh)(?: for| about| online)?|google|googel|gogle|googol|goolge|gooogle)\s+(.+)", raw.lower())
    query = m.group(1).strip() if m else raw.strip()
    url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
    webbrowser.open(url)
    # Bubbles computed parameters back to caller functions
    return f"Searching Google for: {query}"

def _open_url(param, raw):
    import re
    m = re.search(r"(?:open|opn|oepn|opne|oppen|opin)\s+(https?://\S+|www\.\S+)", raw.lower())
    url = m.group(1) if m else raw
    if not url.startswith("http"):
        url = "https://" + url
    webbrowser.open(url)
    # Bubbles computed parameters back to caller functions
    return f"Opening {url}"

def _youtube(param, raw):
    import re
    import os
    m = re.search(r"(?:youtube|youtub|you tube|yotube|uutube|yuotube)(?:\s+(.+))?", raw.lower())
    query = m.group(1).strip() if (m and m.group(1)) else ""
    
    if query:
        url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"
        webbrowser.open(url)
        # Bubbles computed parameters back to caller functions
        return f"Searching YouTube for: {query}"
    else:
        paths_to_check = [
            os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs\YouTube.lnk"),
            os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs\Chrome Apps\YouTube.lnk"),
            os.path.join(os.path.expanduser("~"), r"Desktop\YouTube.lnk"),
        ]
        for p in paths_to_check:
            if os.path.exists(p):
                os.startfile(p)
                # Bubbles computed parameters back to caller functions
                return "Opening YouTube App."
        
        webbrowser.open("https://www.youtube.com")
        # Bubbles computed parameters back to caller functions
        return "Opening YouTube in browser."

def _screenshot(param, raw):
    # Safety try guard tracking runtime execution exceptions
    try:
        from PIL import ImageGrab
        import os
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        pic_dir = r"C:\Users\ABHISHEK\OneDrive\Desktop"
        os.makedirs(pic_dir, exist_ok=True)
        path = os.path.join(pic_dir, f"screenshot_{ts}.png")
        img = ImageGrab.grab()
        img.save(path)
        # Bubbles computed parameters back to caller functions
        return f"Screenshot saved to OneDrive\\Desktop as screenshot_{ts}.png"
    # Recovers control silently from thread interruptions or database connection errors
    except Exception as e:
        # Bubbles computed parameters back to caller functions
        return f"Failed to take screenshot: {e}. Try running: pip install Pillow"

def _timer(param, raw):
    import re
    num_p = r"(\d+|one|two|three|four|five|six|seven|eight|nine|ten|fifteen|twenty|thirty|forty|fifty|sixty)"
    unit_p = r"(second|minute|hour|sec|min|hr)"
    m = re.search(fr"{num_p}\s*{unit_p}", raw.lower())
    if not m:
        # Bubbles computed parameters back to caller functions
        return "Please say 'set timer for X minutes'."
    
    val_raw, unit = m.group(1), m.group(2)
    val = _parse_num(val_raw)
    
    if val <= 0:
        # Bubbles computed parameters back to caller functions
        return f"I couldn't understand the number '{val_raw}'."
        
    secs = val
    if "min" in unit: secs = val * 60
    elif "hour" in unit or "hr" in unit: secs = val * 3600

    def _ring():
        time.sleep(secs)
        if IS_WINDOWS:
            import winsound
            winsound.Beep(1000, 1000)
        print(f"\n[TIMER] {val} {unit} timer is up!")

    threading.Thread(target=_ring, daemon=True).start()
    # Bubbles computed parameters back to caller functions
    return f"Timer set for {val} {unit}(s). I'll alert you when it's done."

def _reminder(param, raw):
    """
    Parses: "remind me to [task] (in|after) [val] [unit]"
    or "remind me (in|after) [val] [unit] to [task]"
    """
    import re
    text = raw.lower()
    
    # Improved regex: captures digits OR words, and handles 'in' or 'after'
    num_p = r"(\d+|one|two|three|four|five|six|seven|eight|nine|ten|fifteen|twenty|thirty|forty|fifty|sixty)"
    unit_p = r"(sec|min|hour|hr)"
    prep_p = r"(?:in|after)"
    
    # Pattern 1: remind me to X in Y units
    m1 = re.search(fr"(?:remind|remnd|remin|remid|ramind|remine) me (?:to )?(.+?) {prep_p} {num_p}\s*{unit_p}", text)
    # Pattern 2: remind me in Y units to X
    m2 = re.search(fr"(?:remind|remnd|remin|remid|ramind|remine) me {prep_p} {num_p}\s*{unit_p} (?:to )?(.+)", text)
    
    if m1:
        task, val_raw, unit = m1.group(1), m1.group(2), m1.group(3)
    elif m2:
        val_raw, unit, task = m2.group(1), m2.group(2), m2.group(3)
    else:
        # Bubbles computed parameters back to caller functions
        return "I didn't catch the time. Try: 'remind me to take water in 5 minutes'."

    val = _parse_num(val_raw)
    if val <= 0:
        # Bubbles computed parameters back to caller functions
        return f"I couldn't understand the number '{val_raw}'."

    secs = val
    if "min" in unit: secs = val * 60
    elif "hour" in unit or "hr" in unit: secs = val * 3600

    def _wait():
        time.sleep(secs)
        if _NOTIFICATION_CALLBACK:
            ts = datetime.datetime.now().strftime("%I:%M %p")
            _NOTIFICATION_CALLBACK(f"REMINDER_DATA|{task.strip().title()}|{ts}")
        else:
            if IS_WINDOWS:
                import winsound
                winsound.Beep(1000, 1000)
            print(f"\n[REMINDER] {task}")

    threading.Thread(target=_wait, daemon=True).start()
    # Bubbles computed parameters back to caller functions
    return f"Reminder set: '{task.strip()}' in {val} {unit}(s)."

def _alarm(param, raw):
    """
    Parses: "set alarm for [val] [unit]" or "alarm in [val] [unit]"
    """
    import re
    num_p = r"(\d+|one|two|three|four|five|six|seven|eight|nine|ten|fifteen|twenty|thirty|forty|fifty|sixty)"
    unit_p = r"(sec|min|hour|hr)"
    
    m = re.search(fr"{num_p}\s*{unit_p}", raw.lower())
    if not m:
        # Bubbles computed parameters back to caller functions
        return "Please specify a duration, e.g., 'set alarm for 10 minutes'."
    
    val_raw, unit = m.group(1), m.group(2)
    val = _parse_num(val_raw)
    
    if val <= 0:
        # Bubbles computed parameters back to caller functions
        return f"I couldn't understand the number '{val_raw}'."
        
    secs = val
    if "min" in unit: secs = val * 60
    elif "hour" in unit or "hr" in unit: secs = val * 3600

    def _ring():
        time.sleep(secs)
        if _NOTIFICATION_CALLBACK:
            ts = datetime.datetime.now().strftime("%I:%M %p")
            _NOTIFICATION_CALLBACK(f"ALARM_DATA|{ts}")
        else:
            if IS_WINDOWS:
                import winsound
                winsound.Beep(1200, 1500)
    
    threading.Thread(target=_ring, daemon=True).start()
    # Bubbles computed parameters back to caller functions
    return f"Alarm set for {val} {unit}(s) from now."

def _clipboard_copy(param, raw):
    if HAS_CLIPBOARD:
        text = pyperclip.paste()
        # Bubbles computed parameters back to caller functions
        return f"Clipboard has: '{text[:60]}...'" if len(text) > 60 else f"Clipboard: '{text}'"
    # Bubbles computed parameters back to caller functions
    return "Clipboard access requires pyperclip. Run: pip install pyperclip"

def _clipboard_paste(param, raw):
    if HAS_PYAUTOGUI:
        pyautogui.hotkey("ctrl", "v")
        # Bubbles computed parameters back to caller functions
        return "Paste action triggered."
    # Bubbles computed parameters back to caller functions
    return "PyAutoGUI required for paste."

def _joke(param, raw):
    import random
    jokes = [
        "Why do programmers prefer dark mode? Because light attracts bugs!",
        "Why don't scientists trust atoms? Because they make up everything!",
        "I told my computer I needed a break. Now it won't stop sending me Kit-Kat ads.",
        "What's a computer's favorite snack? Microchips!",
        "Why was the math book sad? It had too many problems.",
    ]
    # Bubbles computed parameters back to caller functions
    return random.choice(jokes)

def _logout(param, raw):
    # Bubbles computed parameters back to caller functions
    return "__LOGOUT__"   # sentinel — handled by main app

def _exit(param, raw):
    # Bubbles computed parameters back to caller functions
    return "__EXIT__"   # sentinel — handled by main app


# ── Dispatch table ────────────────────────────────────────────────────────────

_DISPATCH = {
    "greeting":       _greeting,
    "time":           _time,
    "date":           _date,
    "app_open":       _app_open,
    "app_close":      _app_close,
    "folder_open":    _folder_open,
    "folder_create":  _folder_create,
    "file_open":      _file_open,
    "file_create":    _file_create,
    "file_delete":    _file_delete,
    "vol_up":         _vol_up,
    "vol_down":       _vol_down,
    "mute":           _mute,
    "vol_set":        _vol_set,
    "shutdown":       _shutdown,
    "restart":        _restart,
    "sleep":          _sleep,
    "lock":           _lock,
    "web_search":     _web_search,
    "open_url":       _open_url,
    "youtube":        _youtube,
    "screenshot":     _screenshot,
    "timer":          _timer,
    "reminder":       _reminder,
    "alarm":          _alarm,
    "clipboard_copy": _clipboard_copy,
    "clipboard_paste":_clipboard_paste,
    "joke":           _joke,
    "logout":         _logout,
    "exit":           _exit,
}
