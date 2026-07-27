# ============================================================
#  EmpowerAccess Desktop — ui/settings_dialog.py
#  Modal settings window: Theme / Profile / How to use
# ============================================================

# Imports standard Tkinter toolkit to manage window elements
import tkinter as tk
from ui.theme import *
from config import APP_NAME, APP_VERSION


# Visual category layout dialog displaying profile management options
class SettingsDialog(tk.Toplevel):

    def __init__(self, master, api_client, section="profile"):
        super().__init__(master)
        self.api = api_client
        self.title(f"{APP_NAME} · Settings")
        self.configure(bg=BG)
        self.resizable(False, False)

        W, H = 560, 420
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"{W}x{H}+{(sw - W) // 2}+{(sh - H) // 2}")
        self.grab_set()

        self._section = section
        self._build()
        self._show_section(section)

    def _build(self):
        # Title bar
        title_bar = frame(self, bg=BG3)
        title_bar.pack(fill="x")
        label(title_bar, text=f"{APP_NAME}  ·  Settings",
              bg=BG3, fg=TEAL2, font=FONT_LG).pack(side="left", padx=16, pady=10)
        tk.Button(title_bar, text="✕", bg=BG3, fg=TEXT2, relief="flat",
                  bd=0, font=FONT_MD, cursor="hand2",
                  command=self.destroy,
                  activebackground=BG4).pack(side="right", padx=12)

        separator(self, bg=BORDER).pack(fill="x")

        body = frame(self, bg=BG2)
        body.pack(fill="both", expand=True)

        # Sidebar
        sidebar = frame(body, bg=BG3)
        sidebar.pack(side="left", fill="y")
        sidebar.configure(width=140)
        sidebar.pack_propagate(False)

        self._nav_btns = {}
        for sec, lbl in [("profile", "👤  Profile"),
                          ("how_to_use", "❓  How to use")]:
            btn = tk.Button(sidebar, text=lbl, anchor="w",
                            bg=BG3, fg=TEXT2, font=FONT_SM,
                            relief="flat", bd=0, padx=16, pady=12,
                            cursor="hand2", activebackground=BG4,
                            command=lambda s=sec: self._show_section(s))
            btn.pack(fill="x")
            self._nav_btns[sec] = btn

        tk.Frame(sidebar, bg=BORDER, height=1).pack(fill="x", pady=8)
        label(sidebar, text=f"v{APP_VERSION}", bg=BG3,
              fg=BORDER, font=FONT_SM).pack(padx=16, anchor="w")

        # Content area
        self._content = frame(body, bg=BG2)
        self._content.pack(side="left", fill="both", expand=True, padx=20, pady=20)

    def _show_section(self, section: str):
        for s, btn in self._nav_btns.items():
            if s == section:
                btn.configure(bg=BG4, fg=TEAL2)
            else:
                btn.configure(bg=BG3, fg=TEXT2)

        for w in self._content.winfo_children():
            w.destroy()

        if section == "profile":
            self._build_profile()
        elif section == "how_to_use":
            self._build_howto()

    # ── Profile section ───────────────────────────────────────────────────────

    def _build_profile(self):
        p = self._content
        label(p, text="Your Profile", bg=BG2, fg=TEXT,
              font=FONT_LG).pack(anchor="w", pady=(0, 16))

        # Imports threading libraries to execute non-blocking updates loops
        import threading
        self._profile_status = label(p, text="Loading profile…",
                                     bg=BG2, fg=TEXT2, font=FONT_SM)
        self._profile_status.pack(anchor="w")

        threading.Thread(target=self._load_profile, daemon=True).start()

    def _load_profile(self):
        res = self.api.get_profile()
        self.after(0, self._render_profile, res)

    def _render_profile(self, res):
        # Safety guard intercepting unexpected GUI or network anomalies
        try:
            if not self.winfo_exists() or not getattr(self, "_content", None) or not self._content.winfo_exists():
                # Bubbles computed parameters back to caller functions
                return
            for w in self._content.winfo_children():
                w.destroy()

            p = self._content
            label(p, text="Your Profile", bg=BG2, fg=TEXT,
                  font=FONT_LG).pack(anchor="w", pady=(0, 16))

            if res.get("success"):
                u = res["user"]
                fields = [
                    ("Name",      u.get("name",               "—")),
                    ("Email",     u.get("email",              "—")),
                    ("Phone",     u.get("phone",              "—")),
                    ("Emergency", u.get("emergency_contact",  "—")),
                    ("City",      u.get("city",               "—")),
                    ("Status",    u.get("status",             "—")),
                    ("Joined",    str(u.get("created_at",     "—"))[:10]),
                ]
                for key, val in fields:
                    row = tk.Frame(p, bg=BORDER)
                    row.pack(fill="x", pady=3)
                    inner_row = frame(row, bg=BG3)
                    inner_row.pack(fill="both", expand=True, padx=1, pady=1, ipadx=10, ipady=7)
                    
                    label(inner_row, text=key, bg=BG3, fg=TEXT2,
                          font=FONT_SM).pack(side="left", padx=10)
                    label(inner_row, text=val, bg=BG3, fg=TEXT,
                          font=FONT_SM).pack(side="right", padx=10)
            else:
                label(p, text=f"Could not load profile: {res.get('message')}",
                      bg=BG2, fg=RED, font=FONT_SM).pack(anchor="w")
        # Recovers control silently from thread interruptions or window disposal errors
        except (tk.TclError, RuntimeError, AttributeError):
            pass

    # ── How to use section ────────────────────────────────────────────────────

    def _build_howto(self):
        p = self._content
        label(p, text="How to Use", bg=BG2, fg=TEXT,
              font=FONT_LG).pack(anchor="w", pady=(0, 12))

        from tkinter import scrolledtext
        st = scrolledtext.ScrolledText(
            p, bg=BG3, fg=TEXT, font=FONT_SM,
            relief="flat", bd=0, state="normal",
            wrap="word", height=30
        )
        st.pack(fill="both", expand=True)

        guide = """
🎤  VOICE COMMANDS
━━━━━━━━━━━━━━━━━
1. Click the MIC button in the toolbar to toggle microphone on/off.
2. When the orb glows teal, it's listening.
3. Speak your command clearly.The application will transcribe it.
4. The response will be spoken back and shown in the chat.

⌨️  TEXT COMMANDS
━━━━━━━━━━━━━━━━━
Type any command in the chat input box and press Enter or click ➤

📋  EXAMPLE COMMANDS
━━━━━━━━━━━━━━━━━━━━
• "What time is it?"
• "Weather in Mumbai"
• "Open Chrome"
• "Open Downloads folder"
• "Volume up"
• "CPU usage"
• "Latest technology news"
• "Stock price of RELIANCE"
• "Search for Python tutorials"
• "Set timer for 5 minutes"
• "Tell me a joke"
• "Explain machine learning"   ← AI assistant 
• "SOS" or "Emergency"         

🔧  TOOLBAR
━━━━━━━━━━
• MIC button    → Toggle microphone on/off
• ▼ / ▲         → Expand / collapse main window
• ⚙            → Open settings
• ✕            → Exit application
• Drag the toolbar to reposition the window anywhere on screen.

🧠  AI FALLBACK
━━━━━━━━━━━━━━━
If a command isn't recognised by the rule engine, it's automatically
sent to Gemini AI for a smart response.

🆘  SOS
━━━━━━
Say "SOS", "Emergency", or click the Emergency SOS button.
An alert is sent to the admin dashboard and your emergency contact
via SMS (Twilio).
        """.strip()

        st.insert("1.0", guide)
        st.configure(state="disabled")
