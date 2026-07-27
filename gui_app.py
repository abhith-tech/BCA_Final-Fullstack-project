# ============================================================
#  EmpowerAccess Desktop — app.py
#  Root application controller
#  Boot order:
#    1. Tk root (hidden)
#    2. Login window → on success → main window
#    3. Toolbar + MainPanel
#    4. Voice loop thread
#    5. Background refresh threads (sysinfo, weather)
# ============================================================

# Imports standard Tkinter package to handle user desktop graphical templates
import tkinter as tk
# Imports threading libraries to execute backend loops without UI freezing
import threading
# Imports time utilities to compute delays, intervals, and active clock timestamps
import datetime
# Imports time utilities to compute delays, intervals, and active clock timestamps
import time
import sys
import os
import re
# Imports global keystroke package enabling shortcut combinations triggers
import keyboard

# Imports global dimensions, layout sizes, and operational configuration parameters
from config import (APP_NAME, APP_VERSION, MAIN_W, MAIN_H,
                    TOOLBAR_W, TOOLBAR_H, THEME, SAMPLE_RATE)
# Imports internal API REST client library to coordinate with backend servers
from core.api_client        import APIClient
# Imports command parser routines separating rules-based logic and AI assistants
from core.command_processor import CommandProcessor 
# Imports audio recording, transcribing, and native text-to-speech speaker modules
from core.voice_engine      import AudioRecorder, transcribe, speak, stop_speech, preload, is_speaking
from core.intent_router     import match_intent
from core.tool_executor     import execute, set_notification_callback
from ui.login_window        import LoginWindow
from ui.toolbar             import Toolbar
from ui.main_panel          import MainPanel
from ui.settings_dialog     import SettingsDialog
from ui.theme               import *


# Main controller class supervising client windows, worker threads, and system hooks
class EmpowerAccessApp:
    """Root application controller."""

    # Constructor initializing connection handlers, audio states, and root containers
    def __init__(self):
        self.api       = APIClient()
        self.processor = CommandProcessor(self.api)
        self.recorder  = AudioRecorder()
        self.recorder.on_level_cb = self._on_audio_level
        set_notification_callback(self._on_background_notification)

        self._user_name  = ""
        self._mic_on     = False
        self._recording  = False
        self._wx_city    = "Bengaluru"   # default city for weather widget
        self._user_city  = ""            # city saved in profile (for SOS)
        self._emergency_contact = ""

        # ── Tk root (hidden container) ────────────────────────────────────
        # Creates parent Tkinter layout window to host sub-level cockpit frames
        self.root = tk.Tk()
        # Hides root frame container to show entry credentials panels cleanly first
        self.root.withdraw()
        self.root.title(APP_NAME)
        self.root.configure(bg=BG)
        apply_global_style(self.root)

        # Preload Whisper + TTS in background immediately
        # Launches asynchronous threads pre-loading speech model weights immediately
        threading.Thread(target=preload, daemon=True).start()

        # ── Check saved token → skip login if valid ───────────────────────
        # Checks if login credential tokens are cached locally to bypass logins
        if self.api.token:
            res = self.api.verify_token()
            if res.get("success"):
                uid  = res["user"].get("user_id", "")
                role = res["user"].get("role", "user")
                # Fetch name
                prof = self.api.get_profile()
                u = prof.get("user", {}) if prof.get("success") else {}
                name = u.get("name", "User")
                self._emergency_contact = u.get("emergency_contact", "")
                self._user_city = u.get("city", "") or self._wx_city
                self.processor.update_user_info(name, self._emergency_contact, self._user_city)
                self.root.after(0, self._safe_ui_update, self._launch_main, name, role)
                self._start_tk()
                # Closes active routine and bubbles back result values
                return

        # ── Show login ────────────────────────────────────────────────────
        self._show_login()
        self._start_tk()

    # Starts main event listener loops blocking processing steps
    def _start_tk(self):
        self.root.mainloop()

    def _safe_ui_update(self, func, *args, **kwargs):
        # Safety guard intercepting unexpected execution faults
        try:
            func(*args, **kwargs)
        # Catches and reports anomalies without crashing main UI loops
        except (tk.TclError, RuntimeError, AttributeError):
            pass

    # ── Login ─────────────────────────────────────────────────────────────────

    # Creates login dialog window blocking other flows till verified
    def _show_login(self):
        self._login_win = LoginWindow(
            self.root, self.api,
            on_success=self._on_login_success
        )
        self.root.wait_window(self._login_win)

    # Login callback retrieving name details and spawning cockpit
    def _on_login_success(self, token, name, role):
        self._login_win.destroy()
        # Fetch full profile to get emergency contact
        prof = self.api.get_profile()
        if prof.get("success"):
            u = prof["user"]
            self._emergency_contact = u.get("emergency_contact", "")
            self._user_city = u.get("city", "") or self._wx_city
            self.processor.update_user_info(name, self._emergency_contact, self._user_city)
        self._launch_main(name, role)

    # ── Main window ───────────────────────────────────────────────────────────

    # Spawns visual panel frames, borderless coordinates, and global hotkeys
    def _launch_main(self, name: str, role: str):
        self._user_name = name

        # ── Main window (borderless) ──────────────────────────────────────
        self._win = tk.Toplevel(self.root)
        self._win.configure(bg=BG)
        self._win.overrideredirect(True)   # removes OS title bar
        self._win.attributes("-topmost", False)

        # Centre on screen
        sw = self._win.winfo_screenwidth()
        sh = self._win.winfo_screenheight()
        x  = (sw - MAIN_W) // 2
        y  = (sh - MAIN_H - 80) // 2
        self._win.geometry(f"{MAIN_W}x{MAIN_H}+{x}+{y}")

        self._win.update_idletasks()
        set_rounded_corners(self._win)

        self._win.protocol("WM_DELETE_WINDOW", self._exit_app)

        # ── Toolbar ───────────────────────────────────────────────────────
        self._toolbar = Toolbar(
            self._win,
            on_mic_toggle     = self._on_mic_toggle,
            on_expand_toggle  = self._on_expand_toggle,
            on_settings_section = self._on_settings_section,
            on_sms_message    = self._on_sms_message,
            on_exit           = self._exit_app,
        )
        self._toolbar.pack(fill="x")

        # Thin separator
        tk.Frame(self._win, bg=BORDER, height=1).pack(fill="x")

        # ── Main panel ────────────────────────────────────────────────────
        self._panel = MainPanel(
            self._win,
            on_command = self._dispatch_command,
            on_sos     = self._trigger_sos,
            on_logout  = self._logout,
            on_stop_voice = stop_speech,
            api        = self.api,
        )
        self._panel.pack(fill="both", expand=True)

        # ── Global Hotkeys ────────────────────────────────────────────────
        # Safety guard intercepting unexpected execution faults
        try:
            keyboard.add_hotkey('alt+b+space', lambda: self.root.after(0, self._toggle_mic_via_shortcut, True))
            keyboard.add_hotkey('alt+n+space', lambda: self.root.after(0, self._toggle_mic_via_shortcut, False))
        # Catches and reports anomalies without crashing main UI loops
        except Exception as e:
            print(f"[Hotkeys] Could not register: {e}")

        # Greet the user
        self._panel.update_greeting(name)
        self._panel.add_system_message(f"Welcome back, {name}! We are unstoppable.")

        # Speak welcome
        speak_name = re.sub(r'([a-zA-Z])(\d)', r'\1 \2', name)
        threading.Thread(
            target=speak,
            args=(f"greetings,{speak_name}.",),
            daemon=True
        ).start()

        # Start background refresh loops
        threading.Thread(target=self._sysinfo_loop, daemon=True).start()
        threading.Thread(target=self._weather_loop, daemon=True).start()

    # ── Command dispatch ──────────────────────────────────────────────────────

    # Central dispatcher parsing natural language and voice queries
    def _dispatch_command(self, text: str):
        """Central dispatcher — called from chat input, voice, or orb click."""

        # Internal signals
        if text == "__ORB_CLICK__":
            self._toggle_mic_via_orb()
            # Closes active routine and bubbles back result values
            return
        if text == "__REFRESH_CARDS__":
            threading.Thread(target=self._refresh_weather, daemon=True).start()
            threading.Thread(target=self._refresh_sysinfo, daemon=True).start()
            # Closes active routine and bubbles back result values
            return
        if text == "__WEATHER_PROFILE__":
            city = self._user_city or self._wx_city
            self._dispatch_command(f"weather in {city}")
            # Closes active routine and bubbles back result values
            return

        # Show in chat immediately
        self._panel.add_user_message(text)
        self._toolbar.update_last_command(text)
        self._toolbar.update_status("Processing")
        self._panel.add_system_message("Processing…")

        def _cb(response: str, intent: str):
            # Sentinels for app-level actions
            if response == "__LOGOUT__":
                self.root.after(0, self._safe_ui_update, self._logout)
                # Closes active routine and bubbles back result values
                return
            if response == "__EXIT__":
                self.root.after(0, self._safe_ui_update, self._exit_app)
                # Closes active routine and bubbles back result values
                return

            # Clean response for speech (don't read out raw NEWS_DATA metadata)
            speech_text = response
            if response.startswith("NEWS_DATA|"):
                parts = response.split("||")
                header = parts[0].split("|")
                cat = header[1] if len(header) > 1 else "News"
                count = len(parts) - 1
                speech_text = f"I've found {count} {cat} news headlines for you."
            elif response.startswith("STOCK_DATA|"):
                fields = response.split("|")
                if len(fields) >= 5:
                    name, price, curr = fields[1], fields[3], fields[4]
                    speech_text = f"The current price for {name} is {price} {curr}."
            elif response.startswith("WEATHER_DATA|"):
                fields = response.split("|")
                if len(fields) >= 6:
                    city, temp, desc = fields[1], fields[2], fields[3]
                    speech_text = f"The weather in {city} is {temp} degrees Celsius and {desc}."
            elif response.startswith("SYS_DATA|"):
                fields = response.split("|")
                if len(fields) >= 10:
                    cpu_p, ram_p = fields[1], fields[4]
                    speech_text = f"System status: CPU is at {cpu_p} percent, and RAM usage at {ram_p} percent."

            self.root.after(0, self._safe_ui_update, self._panel.add_bot_message, response)
            
            # Don't speak if it's an error message
            ERROR_PREFIXES = ("Could not", "System info error", "SOS failed", "AI error", "Processing error", "I couldn't find")
            if intent != "error" and not any(speech_text.startswith(p) for p in ERROR_PREFIXES):
                threading.Thread(target=speak, args=(speech_text,), daemon=True).start()

            # Trigger card refresh after weather/sysinfo commands
            if intent == "weather":
                threading.Thread(target=self._refresh_weather, daemon=True).start()
            elif intent == "sysinfo":
                threading.Thread(target=self._refresh_sysinfo, daemon=True).start()

            self._toolbar.update_status("Executed")
            # Reset to Listening if mic is still on, otherwise Idle, after 3 seconds
            self.root.after(3000, lambda: self._toolbar.update_status("Listening" if self._mic_on else "Idle"))

        self.processor.process(text, _cb)

    # ── Mic / Voice ───────────────────────────────────────────────────────────
    # Microphone active state toggle handler triggering record buffers
    def _on_mic_toggle(self, is_on: bool):
        self._mic_on = is_on
        self._panel.set_mic_active(is_on)
        if is_on:
            self._start_listening()
        else:
            self._stop_listening()
            self._toolbar.update_status("Idle")

    # Microphone toggle callback bound to center visual orb clicks
    def _toggle_mic_via_orb(self):
        """Orb click = toggle mic."""
        new_state = not self._mic_on
        self._toolbar.set_mic_state(new_state)
        self._on_mic_toggle(new_state)

    # Spawns new thread to capture microphone microphone arrays
    def _start_listening(self):
        if self._recording:
            # Closes active routine and bubbles back result values
            return
        self._recording = True
        threading.Thread(target=self._record_and_process, daemon=True).start()

    # Terminates recorder thread buffer and schedules transcriber steps
    def _stop_listening(self):
        self._recording = False
        if self.recorder._recording:
            audio = self.recorder.stop()
            if audio is not None and len(audio) > SAMPLE_RATE * 0.3:
                threading.Thread(target=self._transcribe_and_dispatch,
                                 args=(audio,), daemon=True).start()

    # Dynamic microphone listening loop applying silence threshold timeout detections
    def _record_and_process(self):
        """
        Keep recording while mic is on.
        Uses RMS-based silence detection — much more reliable than
        the old peak-level check which was cutting speech off early.

        Logic:
          - Track RMS level every 100 ms.
          - If RMS drops below SILENCE_FLOOR for SILENCE_TIMEOUT seconds
            after speech was detected -> stop, transcribe, restart.
          - MAX_UTTERANCE_SECS caps a single recording (prevents runaway).
        """
        SILENCE_FLOOR      = 0.008   # RMS below this = silence
        SILENCE_TIMEOUT    = 2.2     # seconds of continuous silence -> process
        MAX_UTTERANCE_SECS = 12.0    # hard cap per utterance
        CHUNK_SECS         = 0.1

        self.recorder.start()
        self.root.after(0, self._toolbar.update_status, "Listening")
        silence_dur  = 0.0
        active_dur   = 0.0
        speech_seen  = False

        while self._recording and self._mic_on:
            time.sleep(CHUNK_SECS)
            active_dur += CHUNK_SECS
            # _last_audio_level is scaled *30 in recorder, undo it here
            rms = getattr(self, "_last_audio_level", 0.0) / 30.0

            if rms > SILENCE_FLOOR:
                speech_seen = True
                silence_dur = 0.0
            else:
                if speech_seen:
                    silence_dur += CHUNK_SECS

            should_process = (
                (speech_seen and silence_dur >= SILENCE_TIMEOUT) or
                active_dur >= MAX_UTTERANCE_SECS
            )

            if should_process:
                audio = self.recorder.stop()
                if audio is not None:
                    self.root.after(0, self._toolbar.update_status, "Processing")
                    threading.Thread(
                        target=self._transcribe_and_dispatch,
                        args=(audio,), daemon=True
                    ).start()
                # Reset for next utterance
                self.recorder.start()
                silence_dur = 0.0
                active_dur  = 0.0
                speech_seen = False

        # Final stop when mic turned off
        if self.recorder._recording:
            audio = self.recorder.stop()
            if audio is not None and speech_seen:
                threading.Thread(
                    target=self._transcribe_and_dispatch,
                    args=(audio,), daemon=True
                ).start()

    # Sends audio bytes to local transcription model retrieving queries text
    def _transcribe_and_dispatch(self, audio):
        if is_speaking():
            # Closes active routine and bubbles back result values
            return
        self.root.after(0, self._toolbar.update_status, "Processing")
        self._panel.add_system_message("Transcribing…")
        text = transcribe(audio)
        if text and len(text.strip()) > 1:
            self.root.after(0, self._safe_ui_update, self._dispatch_command, text)

    # Mic toggle action mapped directly to keyboard combinations hooks
    def _toggle_mic_via_shortcut(self, on: bool):
        """Shortcut-driven mic toggle."""
        self._toolbar.set_mic_state(on)
        self._on_mic_toggle(on)

    def _on_audio_level(self, level: float):
        self._last_audio_level = level

    # ── Expand / collapse ────────────────────────────────────────────────────

    # Collapses or expands client visual panel sizes on toggler clicks
    def _on_expand_toggle(self, is_expanded: bool):
        if is_expanded:
            self._panel.pack(fill="both", expand=True)
            self._win.geometry(f"{MAIN_W}x{MAIN_H}")
        else:
            self._panel.pack_forget()
            self._win.geometry(f"{MAIN_W}x{TOOLBAR_H + 2}")

    # ── Settings ─────────────────────────────────────────────────────────────

    # Shows settings categories directly within current panel views
    def _on_settings_section(self, section: str):
        # Auto-expand the panel if currently collapsed
        if not self._toolbar._expanded:
            self._toolbar._toggle_expand()
        # Show settings inline inside the main panel
        self._panel.show_settings(section)

    # ── SOS ──────────────────────────────────────────────────────────────────

    # Triggers emergency SOS alarm loops speaking warning phrases vocally
    def _on_sms_message(self):
        # Auto-expand the panel if currently collapsed
        if not self._toolbar._expanded:
            self._toolbar._toggle_expand()
        self._panel.show_sms_box()

    def _trigger_sos(self):
        self._panel.add_system_message(" SOS TRIGGERED!")
        speak("Emergency SOS alert sent!", async_mode=False)
        threading.Thread(target=self._send_sos_async, daemon=True).start()

    # Pushes localized emergency alerts payloads to twilio backend alerts systems
    def _send_sos_async(self):
        sos_location = self._user_city or self._wx_city
        res = self.api.trigger_sos(location=sos_location, contact=self._emergency_contact)
        if res.get("success"):
            ts = datetime.datetime.now().strftime("%I:%M %p")
            msg = f"SOS_DATA|{sos_location}|{self._emergency_contact}|{ts}"
        else:
            msg = f"SOS error: {res.get('message')}"
        
        # Dispatch to UI thread
        self.root.after(0, self._panel.add_bot_message, msg)
        self.root.after(0, self._panel.add_system_message, "SOS SEQUENCE COMPLETED")

    # Handles incoming alarm and reminder alerts triggers speaking alerts text
    def _on_background_notification(self, message: str):
        """Called by background threads (reminders, alarms) to notify user."""
        self.root.after(0, self._safe_ui_update, self._panel.add_bot_message, message)
        
        # Prepare speech text
        speech = "Notification"
        if message.startswith("REMINDER_DATA|"):
            parts = message.split("|")
            task = parts[1] if len(parts) > 1 else "something"
            speech = f"Reminder: {task}"
        elif message.startswith("ALARM_DATA|"):
            speech = "Your alarm is ringing!"
        
        threading.Thread(target=speak, args=(speech,), daemon=True).start()

    # ── Background loops ──────────────────────────────────────────────────────

    # Worker thread updating system CPU RAM parameters every 10 seconds
    def _sysinfo_loop(self):
        # Infinite thread loop executing background updates sequences
        while True:
            self._refresh_sysinfo()
            time.sleep(10)

    # Worker thread updating dynamic weather card details every 5 minutes
    def _weather_loop(self):
        # Infinite thread loop executing background updates sequences
        while True:
            self._refresh_weather()
            time.sleep(300)   # refresh every 5 minutes

    def _refresh_sysinfo(self):
        res = self.api.get_sysinfo()
        if res.get("success"):
            self.root.after(0, self._safe_ui_update, self._panel.update_sysinfo, res["data"])

    def _refresh_weather(self):
        res = self.api.get_weather(self._wx_city)
        if res.get("success"):
            self.root.after(0, self._safe_ui_update, self._panel.update_weather, res["data"])

    # ── Logout / Exit ─────────────────────────────────────────────────────────

    # Destroys connection keys locally and returns cockpit back to logins
    def _logout(self):
        threading.Thread(target=self.api.logout, daemon=True).start()
        self._win.destroy()
        self._show_login()

    # Gracefully closes application windows and halts Tk loops processing
    def _exit_app(self):
        threading.Thread(target=self.api.logout, daemon=True).start()
        self.root.after(500, self.root.destroy)


# ── Entry point ───────────────────────────────────────────────────────────────

# Main entry block triggering multi-processing freeze safeguards
if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    EmpowerAccessApp()
