# ============================================================
#  EmpowerAccess Desktop — ui/toolbar.py
#  Draggable floating toolbar (always-on-top bar)
# ============================================================

# Imports standard Tkinter toolkit to manage window elements
import tkinter as tk
import datetime

from ui.theme import *
from config import APP_NAME, DARK_THEME, LIGHT_THEME



# Glassmorphic header layout wrapping settings cog icons, expand/collapse toggles, and status fields
class Toolbar(tk.Frame):
    """
    Slim always-on-top toolbar.
    Callbacks:
        on_mic_toggle(is_on: bool)
        on_expand_toggle(is_expanded: bool)
        on_settings_section(section: str)   # 'profile' | 'how_to_use'
        on_exit()
    """

    def __init__(self, parent, **callbacks):
        super().__init__(parent, bg=BG2, height=48)
        self.pack_propagate(False)

        self._on_mic_toggle   = callbacks.get("on_mic_toggle",   lambda x: None)
        self._on_expand       = callbacks.get("on_expand_toggle",lambda x: None)
        self._on_settings     = callbacks.get("on_settings_section", lambda x: None)
        self._on_sms_message  = callbacks.get("on_sms_message",  lambda: None)
        self._on_exit         = callbacks.get("on_exit",          lambda: None)

        self._mic_on      = False
        self._expanded    = True
        self._session_sec = 0
        self._last_cmd    = "—"
        self._settings_open = False
        self._current_theme = DARK_THEME


        self._build()
        self._tick_session()

        # Drag support
        self.bind("<ButtonPress-1>",   self._drag_start)
        self.bind("<B1-Motion>",       self._drag_motion)

    # ── Build ─────────────────────────────────────────────────────────────────

    def _build(self):
        # Left cluster - increased padding for rounded corner clearance
        left = frame(self, bg=BG2)
        left.pack(side="left", padx=16, fill="y")

        # EA badge
        badge = tk.Canvas(left, bg=BG3, width=28, height=28, bd=0,
                          highlightthickness=1, highlightbackground=BORDER)
        badge.pack(side="left", padx=(0, 8), pady=10)
        badge.create_text(14, 14, text="EA", fill=TEAL2,
                          font=("Segoe UI", 8, "bold"))

        # MIC button
        self._mic_btn = tk.Button(
            left, text="MIC", font=FONT_BADGE,
            bg=BG3, fg=TEXT2, relief="flat", bd=0,
            padx=8, pady=2, cursor="hand2",
            activebackground=BG4,
            command=self._toggle_mic
        )
        self._mic_btn.pack(side="left", padx=(0, 8))
        self._border_frame(left, self._mic_btn)

        # Status dot + label
        self._dot_canvas = tk.Canvas(left, bg=BG2, width=10, height=10,
                                     bd=0, highlightthickness=0)
        self._dot_canvas.pack(side="left", padx=(0, 4))
        self._dot_id = self._dot_canvas.create_oval(1, 1, 9, 9,
                                                     fill=RED, outline="")

        self._mic_label = label(left, text="Mic Offline",
                                bg=BG2, fg=TEXT2, font=FONT_SM, width=9, anchor="w")
        self._mic_label.pack(side="left", padx=(0, 6))

        # Status label (Listening / Processing / Executed)
        self._status_var = tk.StringVar(value="Idle")
        self._status_label = label(left, textvariable=self._status_var,
                                   bg=BG2, fg=TEXT2, font=FONT_SM, width=9, anchor="w")
        self._status_label.pack(side="left", padx=(6, 0))

        # Pipe
        label(left, text="|", bg=BG2, fg="#ffffff", font=FONT_SM).pack(side="left", padx=4)

        # Last command
        self._last_var = tk.StringVar(value='Last: "—"')
        label(left, textvariable=self._last_var, bg=BG2,
              fg=TEXT2, font=FONT_SM).pack(side="left", padx=(0, 4))

       

        #-----------------------------------------Right cluster---------------------------------------------

        # Right cluster - increased padding for rounded corner clearance
        right = frame(self, bg=BG2)
        right.pack(side="right", padx=16, fill="y")

        # pipe
        label(right, text="|", bg=BG2, fg="#ffffff", font=FONT_SM).pack(side="left", padx=4)

        # Session timer
        self._session_var = tk.StringVar(value="Session: 00:00:00")
        label(right, textvariable=self._session_var, bg=BG2,
              fg=TEXT2, font=FONT_SM, width=14, anchor="w").pack(side="left", padx=(0, 10)) 

        # pipe
        label(right, text="|", bg=BG2, fg="#ffffff", font=FONT_SM).pack(side="left", padx=4)

        # Theme toggle
        self._theme_btn = self._icon_btn(right, "☀️", self._toggle_theme)
        self._theme_btn.configure(font=("Segoe UI", 10), width=2, height=1)
        self._theme_btn.pack(side="left", padx=3)

        sms_btn = self._icon_btn(right, "SMS", self._on_sms_message)
        sms_btn.configure(font=("Segoe UI", 8, "bold"), width=4)
        sms_btn.pack(side="left", padx=3)

        # Settings gear
        self._settings_popup = None
        gear = self._icon_btn(right, "⚙", self._toggle_settings)
        gear.pack(side="left", padx=3)


        # Expand/collapse
        self._expand_var = tk.StringVar(value="▼")
        expand = tk.Button(right, textvariable=self._expand_var,
                           font=FONT_SM, bg=BG3, fg=TEAL2,
                           relief="flat", bd=0, padx=6, pady=4,
                           cursor="hand2", activebackground=BG4,
                           command=self._toggle_expand,
                           highlightthickness=1,
                           highlightbackground=TEAL)
        expand.pack(side="left", padx=3)

        # Exit
        ex = tk.Button(right, text="✕", font=FONT_SM,
                       bg=BG3, fg=RED, relief="flat", bd=0,
                       padx=6, pady=4, cursor="hand2",
                       activebackground="#2a1010",
                       command=self._on_exit,
                       highlightthickness=1,
                       highlightbackground="#3a2020")
        ex.pack(side="left", padx=3)

    def _border_frame(self, parent, widget):
        """Visual border wrapper — just highlights on hover."""
        widget.bind("<Enter>", lambda e: widget.config(
            highlightthickness=1, highlightbackground=TEAL,
            highlightcolor=TEAL))
        widget.bind("<Leave>", lambda e: widget.config(
            highlightthickness=0))

    def _icon_btn(self, parent, char, cmd) -> tk.Button:
        btn = tk.Button(parent, text=char, font=FONT_SM,
                        bg=BG3, fg=TEXT2, relief="flat", bd=0,
                        padx=6, pady=4, cursor="hand2",
                        activebackground=BG4,
                        command=cmd)
        btn.bind("<Enter>", lambda e: btn.config(fg=TEAL2))
        btn.bind("<Leave>", lambda e: btn.config(fg=TEXT2))
        # Bubbles computed parameters back to caller functions
        return btn

    # ── Mic toggle ────────────────────────────────────────────────────────────

    def _toggle_mic(self):
        self._mic_on = not self._mic_on
        if self._mic_on:
            self._mic_btn.configure(bg="#0e2e26", fg=TEAL2)
            self._dot_canvas.itemconfig(self._dot_id, fill=GREEN)
            self._mic_label.configure(text="Mic Online", fg=TEAL2)
        else:
            self._mic_btn.configure(bg=BG3, fg=TEXT2)
            self._dot_canvas.itemconfig(self._dot_id, fill=RED)
            self._mic_label.configure(text="Mic Offline", fg=TEXT2)
        self._on_mic_toggle(self._mic_on)

    # ── Expand toggle ─────────────────────────────────────────────────────────

    def _toggle_expand(self):
        self._expanded = not self._expanded
        self._expand_var.set("▼" if self._expanded else "▲")
        self._on_expand(self._expanded)

    # ── Theme toggle ──────────────────────────────────────────────────────────

    def _toggle_theme(self):
        """Switches between Dark and Light themes and updates all widgets."""
        if self._current_theme == DARK_THEME:
            self._current_theme = LIGHT_THEME
            new_icon = "🌙"
        else:
            self._current_theme = DARK_THEME
            new_icon = "☀️"
        
        self._theme_btn.config(text=new_icon)
        update_all_widgets_theme(self.winfo_toplevel(), self._current_theme)


    # ── Settings popup ────────────────────────────────────────────────────────

    def _toggle_settings(self):
        if self._settings_open and self._settings_popup:
            self._settings_popup.destroy()
            self._settings_open = False
            # Bubbles computed parameters back to caller functions
            return

        self._settings_open = True
        popup = tk.Toplevel(self)
        popup.overrideredirect(True)
        popup.configure(bg=BORDER)

        # Position below toolbar
        x = self.winfo_rootx() + self.winfo_width() - 160
        y = self.winfo_rooty() + self.winfo_height() + 2
        popup.geometry(f"160x125+{x}+{y}")

        inner = frame(popup, bg=BG2)
        inner.pack(fill="both", expand=True, padx=1, pady=1)

        items = [
            ("👤 Profile",            "profile"),
            ("❓ How to use",        "how_to_use"),
            ("📘 Use Shortcuts", "usage_guide"),
        ]
        for txt, key in items:
            btn = tk.Button(inner, text=txt, font=FONT_SM,
                            bg=BG2, fg=TEXT2, relief="flat",
                            bd=0, pady=8, anchor="w", padx=14,
                            cursor="hand2", activebackground=BG3,
                            command=lambda k=key: self._pick_settings(k))
            btn.pack(fill="x")
            btn.bind("<Enter>", lambda e, b=btn: b.config(bg=BG3, fg=TEXT))
            btn.bind("<Leave>", lambda e, b=btn: b.config(bg=BG2, fg=TEXT2))

        self._settings_popup = popup

        def _dismiss(e):
            if self._settings_popup:
                self._settings_popup.destroy()
                self._settings_open = False

        popup.bind("<FocusOut>", _dismiss)
        popup.focus_set()

    def _pick_settings(self, key: str):
        """Dismiss the popup, then open the selected settings section."""
        if self._settings_popup:
            # Safety guard intercepting unexpected GUI or network anomalies
            try:
                self._settings_popup.destroy()
            except tk.TclError:
                pass
            self._settings_open  = False
            self._settings_popup = None
        self._on_settings(key)

    # ── Session clock ─────────────────────────────────────────────────────────

    def _tick_session(self):
        # Safety guard intercepting unexpected GUI or network anomalies
        try:
            self._session_sec += 1
            h = self._session_sec // 3600
            m = (self._session_sec % 3600) // 60
            s = self._session_sec % 60
            self._session_var.set(f"Session: {h:02d}:{m:02d}:{s:02d}")
            self.after(1000, self._tick_session)
        except tk.TclError:
            pass

    # ── Public API ────────────────────────────────────────────────────────────

    def update_last_command(self, cmd: str):
        # Safety guard intercepting unexpected GUI or network anomalies
        try:
            short = cmd[:24] + "…" if len(cmd) > 24 else cmd
            self._last_var.set(f'Last: "{short}"')
        except tk.TclError:
            pass

    def set_mic_state(self, on: bool):
        # Safety guard intercepting unexpected GUI or network anomalies
        try:
            if on != self._mic_on:
                self._toggle_mic()
        except tk.TclError:
            pass

    def update_status(self, status: str):
        """Updates the status label (Listening / Processing / Executed)."""
        # Safety guard intercepting unexpected GUI or network anomalies
        try:
            self._status_var.set(status)
            if status.lower() == "listening":
                self._status_label.configure(fg=TEAL2)
            elif status.lower() == "processing":
                self._status_label.configure(fg=GOLD)
            elif status.lower() == "executed":
                self._status_label.configure(fg=GREEN)
            else:
                self._status_label.configure(fg=TEXT2)
        # Recovers control silently from thread interruptions or window disposal errors
        except (tk.TclError, RuntimeError):
            pass

    # ── Drag support ──────────────────────────────────────────────────────────

    def _drag_start(self, event):
        self._drag_x = event.x_root
        self._drag_y = event.y_root
        self._win_x  = self.winfo_toplevel().winfo_x()
        self._win_y  = self.winfo_toplevel().winfo_y()

    def _drag_motion(self, event):
        dx = event.x_root - self._drag_x
        dy = event.y_root - self._drag_y
        nx = self._win_x + dx
        ny = self._win_y + dy
        self.winfo_toplevel().geometry(f"+{nx}+{ny}")
