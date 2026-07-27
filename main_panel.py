# ============================================================
#  EmpowerAccess Desktop — ui/main_panel.py
#  Expanded main window: orb, cards, chat
# ============================================================

# Imports standard Tkinter toolkit to manage window elements
import tkinter as tk
from tkinter import scrolledtext
# Imports threading libraries to execute non-blocking updates loops
import threading
# Imports math routines to calculate orbital rotation angles and sine waves
import math
# Imports time package to compute animations delays and clock formats
import time
import datetime
import webbrowser

from ui.theme import *
from config import APP_NAME




# Primary cockpit dashboard showing grid modules, chat panels, SOS alarms, and system messages
class MainPanel(tk.Frame):
    """
    The expandable main panel below the toolbar.
    Contains:
      Left  → greeting, animated orb, system status card, weather card, utility buttons
      Right → scrollable AI chat + text input + send button
    """

    def __init__(self, parent, on_command, on_sos, on_logout, on_stop_voice=None, api=None, **kw):
        super().__init__(parent, bg=BG2, **kw)
        self._on_command = on_command
        self._on_sos     = on_sos
        self._on_logout  = on_logout
        self._on_stop_voice = on_stop_voice
        self.api         = api



        self._mic_active     = False
        self._orb_angle      = 0.0
        self._recording      = False
        self._sysinfo        = {}
        self._weather        = {}
        self._orb_pulse      = 0.0
        self._audio_level    = 0.0
        # self._particles removed for concentric design

        self._build()
        self._animate_orb()

    # ── Build ─────────────────────────────────────────────────────────────────

    def _build(self):
        # Border
        border = tk.Frame(self, bg=BORDER)
        border.pack(fill="both", expand=True, padx=1, pady=(0, 1))

        inner = frame(border, bg=BG2)
        inner.pack(fill="both", expand=True, padx=1, pady=1)

        # Two columns
        left  = frame(inner, bg=BG2)
        left.pack(side="left", fill="both", padx=(20, 10), pady=20)

        vsep  = tk.Frame(inner, bg=BORDER, width=1)
        vsep.pack(side="left", fill="y", pady=10)

        right = frame(inner, bg=BG2)
        right.pack(side="left", fill="both", expand=True, padx=(10, 16), pady=20)
        right.configure(width=600)
        right.pack_propagate(False)

        self._build_left(left)
        self._build_right(right)

    #------------------------------------------------------------------------Left panel-------------------------------------------------------------------------

    def _build_left(self, parent):
        # Greeting


        self._greeting_label = label(
            parent,
            text="Greetings!!\n",
            bg=BG2, fg=TEXT,
            font=("Segoe UI", 24, "bold"),
            justify="center"
        )
        self._greeting_label.pack(pady=(0, 4))

        label(parent,
              text="EmpowerAccess · AI Accessibility Software",
              bg=BG2, fg=TEXT2, font=FONT_SM).pack(pady=(2, 10))
        label(parent,
              text="Start Empowering Yourself",
              bg=BG2, fg=TEXT2, font=FONT_SM).pack(pady=(0, 8))

        # Orb canvas
        self._orb_canvas = tk.Canvas(parent, bg=BG2, bd=0,
                                     highlightthickness=0,
                                     width=130, height=130)
        self._orb_canvas.pack()
        self._orb_canvas.bind("<Button-1>", lambda e: self._on_command("__ORB_CLICK__"))

        self._orb_status = label(parent, text="Click orb or use MIC to speak",
                                 bg=BG2, fg=TEXT2, font=FONT_SM)
        self._orb_status.pack(pady=(4, 16))

        # Divider
        separator(parent).pack(fill="x", pady=(0, 16))


        # Cards row
        cards_row = frame(parent, bg=BG2)
        cards_row.pack(fill="x")

        self._build_sysinfo_card(cards_row)
        frame(cards_row, bg=BG2, width=10).pack(side="left")
        self._build_weather_card(cards_row)

        # Divider
        separator(parent).pack(fill="x", pady=(16, 8))

        # Heading for Services
        label(parent, text="SERVICES", bg=BG2, fg=TEXT2, font=FONT_CAPS).pack(anchor="w", pady=(0, 6))

        # Utility buttons — three premium action cards in a row
        util = frame(parent, bg=BG2)
        util.pack(fill="x", pady=(0, 0))

        is_dark = (BG == "#000000")
        
        # ── 1. Emergency SOS ────────────────────────────────────────────────
        sos_bg = "#3a0a0a" if is_dark else "#fff5f5"
        sos_fg = "#ff8080" if is_dark else "#c92a2a"
        sos_h  = "#5c1010" if is_dark else "#ffe3e3"
        
        self._sos_btn = RoundedButton(
            util,
            text    = "Emergency SOS",
            icon    = "⚠",           # plain Unicode warning sign — renders in Segoe UI
            icon_fg = "#ff6b6b",
            command = self._on_sos,
            bg      = sos_bg,
            hover_bg= sos_h,
            fg      = sos_fg,
            outline_col = "#c0392b",
            width   = 240,
            height  = 52,
            font    = ("Segoe UI", 8, "bold"),
        )
        self._sos_btn._is_sos_btn = True
        self._sos_btn.pack(side="left", padx=(0, 8))

        # ── 2. Weather ──────────────────────────────────────────────────────
        wx_bg = "#0a1f1f" if is_dark else "#f0fdfa"
        wx_fg = TEAL2     if is_dark else "#0d9488"
        wx_h  = "#0d2e2e" if is_dark else "#ccfbf1"
        
        self._wx_btn = RoundedButton(
            util,
            text    = "Weather",
            icon    = "🌤",           # Sun behind small cloud
            icon_fg = TEAL2,
            command = self._trigger_weather,
            bg      = wx_bg,
            hover_bg= wx_h,
            fg      = wx_fg,
            outline_col = TEAL,
            width   = 240,
            height  = 52,
            font    = ("Segoe UI", 8, "bold"),
        )
        self._wx_btn._is_weather_btn = True
        self._wx_btn.pack(side="left", padx=(0, 8))

        # Utility buttons — row 2
        util2 = frame(parent, bg=BG2)
        util2.pack(fill="x", pady=(8, 0))

        # ── 3. News ─────────────────────────────────────────────────────────
        RoundedButton(
            util2,
            text    = "News",
            icon    = "📰",
            icon_fg = GOLD,
            command = lambda: self._on_command("latest news"),
            bg      = BG3,
            hover_bg= BG4,
            fg      = TEXT2,
            outline_col = BORDER,
            width   = 240,
            height  = 52,
            font    = ("Segoe UI", 8, "bold"),
        ).pack(side="left", padx=(0, 8))

        # ── 4. Stock ────────────────────────────────────────────────────────
        RoundedButton(
            util2,
            text    = "Stock",
            icon    = "📈",
            icon_fg = GREEN,
            command = lambda: self._on_command("stock market"),
            bg      = BG3,
            hover_bg= BG4,
            fg      = TEXT2,
            outline_col = BORDER,
            width   = 240,
            height  = 52,
            font    = ("Segoe UI", 8, "bold"),
        ).pack(side="left", padx=(0, 8))

        # Divider between primary actions and shortcuts
        separator(parent).pack(fill="x", pady=(16, 8))

        # Heading for Quick Actions
        label(parent, text="QUICK ACTIONS", bg=BG2, fg=TEXT2, font=FONT_CAPS).pack(anchor="w", pady=(0, 6))

        # App Shortcuts — second row
        apps_row = frame(parent, bg=BG2)
        apps_row.pack(fill="x", pady=(0, 0))

        # ── 4. Settings ─────────────────────────────────────────────────────
        RoundedButton(
            apps_row,
            text    = "Settings",
            icon    = "⚙",
            icon_fg = TEXT2,
            command = lambda: self._on_command("open settings"),
            bg      = BG3,
            hover_bg= BG4,
            fg      = TEXT2,
            outline_col = BORDER,
            width   = 120,
            height  = 52,
            font    = ("Segoe UI", 8, "bold"),
        ).pack(side="left", padx=(0, 8))

        # ── 5. Chrome ───────────────────────────────────────────────────────
        RoundedButton(
            apps_row,
            text    = "Chrome",
            icon    = "🌐",
            icon_fg = "#4285F4",
            command = lambda: self._on_command("open chrome"),
            bg      = BG3,
            hover_bg= BG4,
            fg      = TEXT2,
            outline_col = BORDER,
            width   = 120,
            height  = 52,
            font    = ("Segoe UI", 8, "bold"),
        ).pack(side="left", padx=(0, 8))

        # ── 6. Calculator ───────────────────────────────────────────────────
        RoundedButton(
            apps_row,
            text    = "Calc",
            icon    = "🖩",
            icon_fg = "#00a884",
            command = lambda: self._on_command("open calculator"),
            bg      = BG3,
            hover_bg= BG4,
            fg      = TEXT2,
            outline_col = BORDER,
            width   = 120,
            height  = 52,
            font    = ("Segoe UI", 8, "bold"),
        ).pack(side="left", padx=(0, 8))

        # ── 7. Logout ───────────────────────────────────────────────────────
        RoundedButton(
            apps_row,
            text    = "Logout",
            icon    = "⏻",           # plain Unicode power symbol — renders in Segoe UI
            icon_fg = TEXT2,
            command = self._on_logout,
            bg      = BG3,
            hover_bg= BG4,
            fg      = TEXT2,
            outline_col = BORDER,
            width   = 120,
            height  = 52,
            font    = ("Segoe UI", 8, "bold"),
        ).pack(side="left")

        # App Shortcuts — third row
        apps_row2 = frame(parent, bg=BG2)
        apps_row2.pack(fill="x", pady=(8, 0))

        # ── 8. Excel ────────────────────────────────────────────────────────
        RoundedButton(
            apps_row2,
            text    = "Excel",
            icon    = "📊",
            icon_fg = "#217346",
            command = lambda: self._on_command("open excel"),
            bg      = BG3,
            hover_bg= BG4,
            fg      = TEXT2,
            outline_col = BORDER,
            width   = 120,
            height  = 52,
            font    = ("Segoe UI", 8, "bold"),
        ).pack(side="left", padx=(0, 8))

        # ── 9. Word ─────────────────────────────────────────────────────────
        RoundedButton(
            apps_row2,
            text    = "Word",
            icon    = "📝",
            icon_fg = "#2b579a",
            command = lambda: self._on_command("open word"),
            bg      = BG3,
            hover_bg= BG4,
            fg      = TEXT2,
            outline_col = BORDER,
            width   = 120,
            height  = 52,
            font    = ("Segoe UI", 8, "bold"),
        ).pack(side="left", padx=(0, 8))

        # ── 10. YouTube ─────────────────────────────────────────────────────
        RoundedButton(
            apps_row2,
            text    = "YouTube",
            icon    = "▶",
            icon_fg = "#ff0000",
            command = lambda: self._on_command("open youtube"),
            bg      = BG3,
            hover_bg= BG4,
            fg      = TEXT2,
            outline_col = BORDER,
            width   = 120,
            height  = 52,
            font    = ("Segoe UI", 8, "bold"),
        ).pack(side="left", padx=(0, 8))

        # ── 11. Paint ───────────────────────────────────────────────────────
        RoundedButton(
            apps_row2,
            text    = "Paint",
            icon    = "🎨",
            icon_fg = "#00a8e8",
            command = lambda: self._on_command("open paint"),
            bg      = BG3,
            hover_bg= BG4,
            fg      = TEXT2,
            outline_col = BORDER,
            width   = 120,
            height  = 52,
            font    = ("Segoe UI", 8, "bold"),
        ).pack(side="left")


    def _build_sysinfo_card(self, parent):
        outer = tk.Frame(parent, bg=BORDER)
        outer.pack(side="left", fill="both", expand=True)
        inner = tk.Frame(outer, bg=BG3, padx=12, pady=10)
        inner.pack(fill="both", expand=True, padx=1, pady=1)

        label(inner, text="SYSTEM STATUS", bg=BG3, fg=TEXT2,
              font=FONT_CAPS).pack(anchor="w", pady=(0, 8))

        self._sys_rows = {}
        defs = [
            ("CPU",     GREEN, "—"),
            ("RAM",     GREEN, "—"),
            ("Disk",    BLUE,  "—"),
            ("Battery", GOLD,  "—"),
        ]
        for name, color, val in defs:
            row = frame(inner, bg=BG3)
            row.pack(fill="x", pady=1)
            label(row, text=name, bg=BG3, fg=TEXT2, font=FONT_SM).pack(side="left")
            val_lbl = label(row, text=val, bg=BG3, fg=color, font=FONT_SM)
            val_lbl.pack(side="right")

            bar_bg = tk.Frame(inner, bg=BORDER, height=3)
            bar_bg.pack(fill="x", pady=(0, 4))
            bar_fill = tk.Frame(bar_bg, bg=color, height=3)
            bar_fill.place(x=0, y=0, relheight=1, relwidth=0.5)

            self._sys_rows[name] = (val_lbl, bar_fill)

    def _build_weather_card(self, parent):
        outer = tk.Frame(parent, bg=BORDER)
        outer.pack(side="left", fill="both", expand=True)
        inner = tk.Frame(outer, bg=BG3, padx=12, pady=10)
        inner.pack(fill="both", expand=True, padx=1, pady=1)

        label(inner, text="WEATHER STATUS", bg=BG3, fg=TEXT2,
              font=FONT_CAPS).pack(anchor="w", pady=(0, 8))

        self._wx_city  = label(inner, text="—", bg=BG3, fg=TEAL2, font=FONT_MD)
        self._wx_city.pack(anchor="w")
        self._wx_temp  = label(inner, text="—°C", bg=BG3, fg=TEAL2,
                               font=("Segoe UI", 20, "bold"))
        self._wx_temp.pack(anchor="w", pady=(4, 0))
        self._wx_desc  = label(inner, text="—", bg=BG3, fg=TEXT2, font=FONT_SM)
        self._wx_desc.pack(anchor="w", pady=(2, 8))

        sub_row = frame(inner, bg=BG3)
        sub_row.pack(fill="x")
        self._wx_hum  = label(sub_row, text="Humidity: —", bg=BG3,
                              fg=TEXT2, font=FONT_SM)
        self._wx_hum.pack(side="left", padx=(0, 12))
        self._wx_wind = label(sub_row, text="Wind: —", bg=BG3,
                              fg=TEXT2, font=FONT_SM)
        self._wx_wind.pack(side="left")

    # ------------------------------------------------ Right panel (two switchable views: chat / settings) -------------------------------------------------

    def _build_right(self, parent):
        """Create two mutually-exclusive frames: chat view and settings view."""
        self._chat_area = frame(parent, bg=BG2)
        self._chat_area.pack(fill="both", expand=True)

        self._settings_area = frame(parent, bg=BG2)
        # Not packed initially — revealed by show_settings()

        self._build_chat_area(self._chat_area)
        self._build_settings_area(self._settings_area)

    def _build_chat_area(self, parent):
        #---------------------------Chat Header---------------------------
        hdr = frame(parent, bg=BG2)
        hdr.pack(fill="x", pady=(0, 12))

        # Icon + Title
        icon_lbl = label(hdr, bg=BG2, font=("Segoe UI", 14))
        icon_lbl.pack(side="left", padx=(0, 8))

        label(hdr, text="AI ASSISTANT", bg=BG2, fg=TEAL2,
              font=("Segoe UI", 10, "bold")).pack(side="left")

        #----------------------Live status----------------------
        status_frame = frame(hdr, bg=BG2)
        status_frame.pack(side="right")

        label(status_frame, text="LIVE", bg=BG2, fg=TEXT2,
              font=("Segoe UI", 8, "bold")).pack(side="left", padx=4)

        dot_c = tk.Canvas(status_frame, bg=BG2, width=8, height=8, bd=0,
                          highlightthickness=0)
        dot_c.pack(side="left", pady=2)
        dot_c.create_oval(1, 1, 7, 7, fill=GREEN, outline="")
        self._after_pulse(dot_c)

        #------------------------------Chat area-----------------------------
        chat_container = tk.Frame(parent, bg=BG4)
        chat_container.pack(fill="both", expand=True)

        from tkinter import ttk
        self._scrollbar = ttk.Scrollbar(
            chat_container, orient="vertical",
            style="Smooth.Vertical.TScrollbar"
        )
        self._scrollbar.pack(side="right", fill="y", padx=2, pady=2)

        self._chat = tk.Text(
            chat_container, bg=BG4, fg=TEXT,
            font=("Segoe UI", 10), relief="flat", bd=0,
            state="disabled", wrap="word",
            insertbackground=TEXT,
            selectbackground=TEAL, selectforeground="#fff",
            height=22, padx=12, pady=10, yscrollcommand=self._scrollbar.set
        )
        self._chat.pack(side="left", fill="both", expand=True)
        self._scrollbar.configure(command=self._chat.yview)

        # Enable scrolling even when mouse is over the chat text widget itself
        self._chat.bind("<MouseWheel>", self._on_mouse_wheel)

        # Tag Styles
        is_dark = (BG == "#000000")
        self._chat.tag_configure("user",     foreground=TEXT,  justify="right",
                                  lmargin1=80, lmargin2=80, rmargin=10,
                                  spacing1=12, spacing3=4)
        self._chat.tag_configure("bot",      foreground=TEAL2, justify="left",
                                  rmargin=80, lmargin1=10, lmargin2=10,
                                  spacing1=12, spacing3=4)
        
        # Restore slightly gray backgrounds for dark theme bubbles
        u_bg = "#0c0c0c" if is_dark else BG4
        b_bg = "#050505" if is_dark else BG3
        t_fg = "white"   if is_dark else TEXT2

        self._chat.tag_configure("user_msg", background=u_bg, font=("Segoe UI", 10))
        self._chat.tag_configure("bot_msg",  background=b_bg, font=("Segoe UI", 10))
        self._chat.tag_configure("time",     foreground=t_fg, font=("Segoe UI", 8),
                                  justify="right")
        self._chat.tag_configure("sys",      foreground=GOLD,   font=("Segoe UI", 8, "italic"),
                                  justify="center", spacing1=10)
        self._chat.tag_configure("error",    foreground=RED,    font=FONT_SM)

        #---------------------------SMS Message Box-----------------------------
        self._sms_outer_visible = False
        self._sms_outer = frame(parent, bg=BORDER)

        sms_inner = frame(self._sms_outer, bg=BG4)
        sms_inner.pack(fill="both", expand=True, padx=1, pady=1)

        sms_top = frame(sms_inner, bg=BG4)
        sms_top.pack(fill="x", padx=12, pady=(10, 6))

        label(sms_top, text="SMS MESSAGE", bg=BG4, fg=GOLD,
              font=("Segoe UI", 8, "bold")).pack(side="left")

        close_sms = tk.Button(
            sms_top, text="x", command=self.hide_sms_box,
            bg=BG3, fg=TEXT2, activebackground=BG, activeforeground=RED,
            relief="flat", bd=0, font=("Segoe UI", 8, "bold"),
            cursor="hand2", width=2
        )
        close_sms.pack(side="right", padx=(8, 0))

        self._sms_recipient = tk.StringVar(value="emergency")
        sms_menu = tk.OptionMenu(sms_top, self._sms_recipient,
                                 "emergency", "phone")
        sms_menu.configure(
            bg=BG3, fg=TEXT, activebackground=BG, activeforeground=TEAL2,
            relief="flat", bd=0, highlightthickness=0,
            font=("Segoe UI", 8), cursor="hand2"
        )
        sms_menu["menu"].configure(bg=BG3, fg=TEXT, activebackground=TEAL)
        sms_menu.pack(side="right")

        sms_body = frame(sms_inner, bg=BG4)
        sms_body.pack(fill="x", padx=12, pady=(0, 10))

        self._sms_input = tk.Text(
            sms_body, bg=BG3, fg=TEXT, insertbackground=TEXT,
            relief="flat", bd=0, font=("Segoe UI", 9),
            height=3, wrap="word", padx=10, pady=8
        )
        self._sms_input.pack(side="left", fill="both", expand=True)
        self._sms_input.bind("<Control-Return>", self._send_sms_text)
        self._sms_input.bind("<MouseWheel>", self._on_mouse_wheel)

        sms_actions = frame(sms_body, bg=BG4)
        sms_actions.pack(side="right", fill="y", padx=(8, 0))

        self._sms_send_btn = tk.Button(
            sms_actions, text="SEND", command=self._send_sms_text,
            bg=TEAL, fg="#ffffff", font=("Segoe UI", 9, "bold"),
            relief="flat", bd=0, cursor="hand2",
            activebackground=TEAL2, activeforeground="#ffffff",
            disabledforeground="#d8fff6",
            width=10, height=2,
            highlightthickness=1, highlightbackground=TEAL2,
            padx=10, pady=2
        )
        self._sms_send_btn.pack(fill="x", ipady=2)
        self._sms_send_btn.bind("<Enter>", lambda e: self._sms_send_btn.config(bg=TEAL2))
        self._sms_send_btn.bind("<Leave>", lambda e: self._sms_send_btn.config(bg=TEAL))

        self._sms_status = label(
            sms_actions, text="Emergency", bg=BG4, fg=TEXT2,
            font=("Segoe UI", 8)
        )
        self._sms_status.pack(fill="x", pady=(8, 0))

        #---------------------------Input Area-----------------------------
        inp_container = frame(parent, bg=BORDER)
        self._input_container = inp_container
        inp_container.pack(fill="x", pady=(12, 0))

        inner_inp = frame(inp_container, bg=BG4)
        inner_inp.pack(fill="both", expand=True, padx=1, pady=1)

        self._chat_input = tk.Entry(
            inner_inp, bg=BG4, fg=TEXT, insertbackground=TEXT,
            relief="flat", bd=0, font=("Segoe UI", 10),
            highlightthickness=0
        )
        self._chat_input.pack(side="left", fill="x", expand=True,
                               ipady=9, padx=12)
        self._chat_input.bind("<Return>", self._send_text)
        
        # Enable scrolling even from the input box
        self._chat_input.bind("<MouseWheel>", self._on_mouse_wheel)
        inner_inp.bind("<MouseWheel>", self._on_mouse_wheel)

        #send button
        send_btn = tk.Button(inner_inp, text="➤", command=self._send_text,
                             bg=BG, fg=TEAL2, font=("Segoe UI", 14),
                             relief="flat", bd=0, cursor="hand2",
                             activebackground=BG, activeforeground=TEAL)
        send_btn.pack(side="right", padx=8)

      # Stop button
        self._stop_btn = tk.Button(inner_inp, text="⏹", command=self._on_stop_voice,
                             bg=BG, fg=RED, font=("Segoe UI", 14),
                             relief="flat", bd=0, cursor="hand2",
                             activebackground=BG, activeforeground="#a00")
        self._stop_btn.pack(side="right", padx=4)

        
        # Focus effect
        def _on_focus(e):  inp_container.config(bg=TEAL)
        def _off_focus(e): inp_container.config(bg=BORDER)
        self._chat_input.bind("<FocusIn>",  _on_focus)
        self._chat_input.bind("<FocusOut>", _off_focus)

    def _on_mouse_wheel(self, event):
        """Redirect mouse wheel events to the chat widget."""
        self._chat.yview_scroll(int(-1 * (event.delta / 120)), "units")
        # Bubbles computed parameters back to caller functions
        return "break"

    def _enable_bubble_scrolling(self, widget):
        """Recursively bind mouse wheel to a widget and all its children."""
        widget.bind("<MouseWheel>", self._on_mouse_wheel)
        for child in widget.winfo_children():
            self._enable_bubble_scrolling(child)

    def _build_settings_area(self, parent):
        """Build the inline settings panel (hidden until show_settings() is called)."""
        # ── Header bar ────────────────────────────────────
        hdr = frame(parent, bg=BG3)
        hdr.pack(fill="x")

        label(hdr, text="⚙  Settings", bg=BG3, fg=TEAL2,
              font=FONT_MD).pack(side="left", padx=16, pady=12)

        tk.Button(hdr, text="✕  Back to Chat", bg=BG3, fg=TEXT2,
                  relief="flat", bd=0, font=FONT_SM, cursor="hand2",
                  activebackground=BG4,
                  command=self._close_settings).pack(side="right", padx=12, pady=8)

        # ── Tab navigation ────────────────────────────────
        tab_bar = frame(parent, bg=BG4)
        tab_bar.pack(fill="x")

        self._settings_nav_btns = {}
        for sec, lbl_txt in [("profile",     "👤  Profile"),
                              ("how_to_use",  "❓  How to Use"),
                              ("usage_guide", "📘  Usage & Shortcuts")]:
            btn = tk.Button(tab_bar, text=lbl_txt, font=FONT_SM,
                            bg=BG4, fg=TEXT2, relief="flat", bd=0,
                            padx=14, pady=9, cursor="hand2",
                            activebackground=BG3,
                            command=lambda s=sec: self._settings_show_section(s))
            btn.pack(side="left")
            self._settings_nav_btns[sec] = btn

        # Divider
        tk.Frame(parent, bg=BORDER, height=1).pack(fill="x")

        # ── Scrollable content canvas ─────────────────────
        from tkinter import ttk
        scroll_outer = frame(parent, bg=BG2)
        scroll_outer.pack(fill="both", expand=True)

        sc_bar = ttk.Scrollbar(scroll_outer, orient="vertical")
        sc_bar.pack(side="right", fill="y")

        self._settings_canvas = tk.Canvas(scroll_outer, bg=BG2, bd=0,
                                          highlightthickness=0,
                                          yscrollcommand=sc_bar.set)
        self._settings_canvas.pack(side="left", fill="both", expand=True)
        sc_bar.configure(command=self._settings_canvas.yview)

        self._settings_content = frame(self._settings_canvas, bg=BG2)
        self._settings_win_id  = self._settings_canvas.create_window(
            (0, 0), window=self._settings_content, anchor="nw"
        )

        def _on_canvas_resize(e):
            # Safety guard intercepting unexpected GUI or network anomalies
            try:
                self._settings_canvas.itemconfig(self._settings_win_id, width=e.width)
            except tk.TclError:
                pass

        def _on_content_change(e):
            # Safety guard intercepting unexpected GUI or network anomalies
            try:
                self._settings_canvas.configure(
                    scrollregion=self._settings_canvas.bbox("all"))
            except tk.TclError:
                pass

        self._settings_canvas.bind("<Configure>", _on_canvas_resize)
        self._settings_content.bind("<Configure>", _on_content_change)

    def _after_pulse(self, canvas):
        """Pulse the live dot in the chat header."""
        # Safety guard intercepting unexpected GUI or network anomalies
        try:
            items = canvas.find_all()
            if items:
                cur = canvas.itemcget(items[0], "fill")
                canvas.itemconfig(items[0], fill=GREEN if cur == BG2 else BG2)
            self.after(900, lambda: self._after_pulse(canvas))
        except tk.TclError:
            pass

    # ── Orb animation ─────────────────────────────────────────────────────────

    # Animates concentric glowing arcs and central pulsar pulses on local canvas
    def _animate_orb(self):
        # Safety guard intercepting unexpected GUI or network anomalies
        try:
            c = self._orb_canvas
            c.delete("all")
            W, H = 130, 130
            cx, cy = W // 2, H // 2

            self._orb_angle += 0.04
            self._orb_pulse = (math.sin(time.time() * 2.5) + 1) / 2
            self._audio_level *= 0.90
            
            vu_boost = min(1.0, self._audio_level * 18)
            # Unified scale for all rings
            base_scale = 1.0 + (vu_boost * 0.3)
            pulse_scale = base_scale + (0.05 * self._orb_pulse)

            is_dark = (BG == "#000000")
            
            # 1. Background Aura (Static subtle depth)
            aura_col = "#000000" if is_dark else BG2
            c.create_oval(cx - 50, cy - 50, cx + 50, cy + 50,
                          fill=aura_col, outline="")

            # 2. Outer Pulse Ring (Expanding/Fading)
            r_outer = int(58 * pulse_scale)
            if is_dark:
                o_col = f"#{0:02x}{int(40 + 40 * vu_boost):02x}{int(25 + 25 * vu_boost):02x}"
            else:
                # Soft teal glow for light mode
                o_col = f"#{int(200 - 50 * vu_boost):02x}{int(240 - 20 * vu_boost):02x}{int(235 - 10 * vu_boost):02x}"
            
            c.create_oval(cx - r_outer, cy - r_outer, cx + r_outer, cy + r_outer,
                          outline=o_col, width=1)

            # 3. Middle Rotating Rings (Two broken arcs)
            ring_col = TEAL if self._mic_active else (TEAL2 if is_dark else BORDER)
            
            # Ring A: Clockwise rotation
            r_a = int(46 * pulse_scale)
            angle_a = math.degrees(self._orb_angle)
            c.create_arc(cx - r_a, cy - r_a, cx + r_a, cy + r_a,
                         start=angle_a, extent=120, outline=ring_col, 
                         style="arc", width=2)
            c.create_arc(cx - r_a, cy - r_a, cx + r_a, cy + r_a,
                         start=angle_a + 180, extent=120, outline=ring_col, 
                         style="arc", width=2)

            # Ring B: Counter-clockwise rotation
            r_b = int(40 * base_scale)
            angle_b = math.degrees(-self._orb_angle * 1.5)
            c_ring_b = TEAL2 if is_dark else TEAL
            c.create_arc(cx - r_b, cy - r_b, cx + r_b, cy + r_b,
                         start=angle_b, extent=90, outline=c_ring_b, 
                         style="arc", width=1)
            c.create_arc(cx - r_b, cy - r_b, cx + r_b, cy + r_b,
                         start=angle_b + 120, extent=90, outline=c_ring_b, 
                         style="arc", width=1)
            c.create_arc(cx - r_b, cy - r_b, cx + r_b, cy + r_b,
                         start=angle_b + 240, extent=90, outline=c_ring_b, 
                         style="arc", width=1)

            # 4. Central Sharp Core
            core_r = int(22 * base_scale)
            core_fill = "#000000" if is_dark else "#ffffff"
            core_outline = TEAL if self._mic_active else (TEAL2 if is_dark else BORDER)
            c.create_oval(cx - core_r, cy - core_r, cx + core_r, cy + core_r,
                          fill=core_fill, outline=core_outline, width=2)
            
            # Energy Pulsar inside core
            p_r = int(12 * (0.8 + 0.4 * vu_boost))
            pulsar_fill = TEAL if vu_boost > 0.2 else core_fill
            c.create_oval(cx - p_r, cy - p_r, cx + p_r, cy + p_r,
                          fill=pulsar_fill, outline="")

            # 5. Glossy highlight
            h_col = "#1c3d52" if is_dark else "#e0f2f1"
            c.create_oval(cx - 8, cy - 12, cx + 2, cy - 4,
                          fill=h_col, outline="")

            self.after(30, self._animate_orb)
        except tk.TclError:
            pass
        except tk.TclError:
            pass

    # ── Public update API ─────────────────────────────────────────────────────

    def set_mic_active(self, active: bool):
        # Safety guard intercepting unexpected GUI or network anomalies
        try:
            self._mic_active = active
            if active:
                self._orb_status.configure(text="● Listening…", fg=TEAL2)
            else:
                self._orb_status.configure(text="Click orb or use MIC to speak", fg=TEXT2)
        except tk.TclError:
            pass

    def set_audio_level(self, level: float):
        """Update VU level for orb responsiveness."""
        self._audio_level = level
        # Smooth drop-off handled in animation loop

    def update_greeting(self, name: str = ""):
        # Safety guard intercepting unexpected GUI or network anomalies
        try:
            hour = datetime.datetime.now().hour
            if hour < 12:
                g = f"Good Morning{', ' + name if name else ''}!"
            elif hour < 17:
                g = f"Good Afternoon{', ' + name if name else ''}!"
            else:
                g = f"Good Evening{', ' + name if name else ''}!"
            self._greeting_label.configure(text=g)
        except tk.TclError:
            pass

    def update_sysinfo(self, data: dict):
        # Safety guard intercepting unexpected GUI or network anomalies
        try:
            self._sysinfo = data
            if not data:
                # Bubbles computed parameters back to caller functions
                return

            def _pct_width(val):
                # Safety guard intercepting unexpected GUI or network anomalies
                try:
                    # Bubbles computed parameters back to caller functions
                    return min(1.0, float(val) / 100)
                # Recovers control silently from thread interruptions or window disposal errors
                except Exception:
                    # Bubbles computed parameters back to caller functions
                    return 0.0

            updates = {
                "CPU":     (f"{data.get('cpu_percent', '—')}%",  _pct_width(data.get('cpu_percent', 0))),
                "RAM":     (f"{data.get('ram_used', '—')} GB",   _pct_width(data.get('ram_percent', 0))),
                "Disk":    (f"{data.get('disk_used', '—')} GB",  _pct_width(data.get('disk_percent', 0))),
                "Battery": (
                    f"{data.get('battery', 'N/A')}%" if data.get('battery') else "N/A",
                    _pct_width(data.get('battery', 0))
                ),
            }
            for name, (val, pct) in updates.items():
                if name in self._sys_rows:
                    lbl, bar = self._sys_rows[name]
                    lbl.configure(text=val)
                    bar.place(x=0, y=0, relheight=1, relwidth=pct)
        except tk.TclError:
            pass

    def update_weather(self, data: dict):
        # Safety guard intercepting unexpected GUI or network anomalies
        try:
            self._weather = data
            if not data:
                # Bubbles computed parameters back to caller functions
                return
            self._wx_city.configure(text=data.get("city", "—"))
            self._wx_temp.configure(text=f"{data.get('temperature', '—')}°C")
            self._wx_desc.configure(text=data.get("description", "—"))
            self._wx_hum.configure(text=f"Humidity: {data.get('humidity', '—')}%")
            self._wx_wind.configure(text=f"Wind: {data.get('wind_speed', '—')} km/h")
        except tk.TclError:
            pass

    def _refresh_cards(self):
        self._on_command("__REFRESH_CARDS__")

    def _trigger_weather(self):
        self._on_command("__WEATHER_PROFILE__")

    # ── Chat helpers ──────────────────────────────────────────────────────────

    def show_sms_box(self):
        """Open and focus the desktop SMS composer."""
        try:
            if self._settings_area.winfo_ismapped():
                self._close_settings()
            if not self._sms_outer_visible:
                self._sms_outer.pack(fill="x", pady=(12, 0), before=self._input_container)
                self._sms_outer_visible = True
            self._sms_input.focus_set()
        except tk.TclError:
            pass

    def hide_sms_box(self):
        """Hide the desktop SMS composer."""
        try:
            self._sms_outer.pack_forget()
            self._sms_outer_visible = False
        except tk.TclError:
            pass

    def _send_text(self, event=None):
        txt = self._chat_input.get().strip()
        if not txt:
            # Bubbles computed parameters back to caller functions
            return
        self._chat_input.delete(0, "end")
        # Removed add_user_message(txt) to fix duplication bug
        self._on_command(txt)

    def _send_sms_text(self, event=None):
        if not self.api:
            self._set_sms_status("API missing", RED)
            return "break"

        txt = self._sms_input.get("1.0", "end").strip()
        if not txt:
            self._set_sms_status("Type a message", RED)
            return "break"

        if len(txt) > 500:
            self._set_sms_status("Max 500 chars", RED)
            return "break"

        recipient = self._sms_recipient.get()
        self._sms_send_btn.configure(state="disabled", text="SENDING")
        self._set_sms_status("Sending...", GOLD)
        self.add_user_message(f"SMS to {recipient}: {txt}")

        threading.Thread(
            target=self._send_sms_async,
            args=(txt, recipient),
            daemon=True
        ).start()
        return "break"

    def _send_sms_async(self, message: str, recipient: str):
        res = self.api.send_sms_message(message, recipient)
        self.after(0, self._finish_sms_send, res)

    def _finish_sms_send(self, res: dict):
        self._sms_send_btn.configure(state="normal", text="SEND")
        if res.get("success"):
            self._sms_input.delete("1.0", "end")
            to_number = res.get("to", "")
            suffix = f" to {to_number}" if to_number else ""
            self._set_sms_status("Sent", GREEN)
            self.add_bot_message(f"SMS sent successfully{suffix}.")
        else:
            msg = res.get("message", "SMS failed")
            self._set_sms_status("Failed", RED)
            self.add_bot_message(f"SMS failed: {msg}")

    def _set_sms_status(self, text: str, color: str):
        try:
            self._sms_status.configure(text=text, fg=color)
        except tk.TclError:
            pass

    def _smart_scroll(self, force=False):
        """Only scroll to end if already near the end or if forced."""
        if force or self._chat.yview()[1] > 0.92:
            self.after(50, lambda: self._chat.see("end"))

    def add_user_message(self, text: str):
        self._append_msg(text, "user")
        self._smart_scroll(force=True)

    def add_bot_message(self, text: str):
        self._append_msg(text, "bot")
        self._smart_scroll()

    def add_system_message(self, text: str):
        self._chat.configure(state="normal")
        self._chat.insert("end", f"── {text} ──\n", "sys")
        self._smart_scroll()
        self._chat.configure(state="disabled")

    def _append_msg(self, text: str, role: str):
        self._chat.configure(state="normal")
        ts     = datetime.datetime.now().strftime("%I:%M %p")
        is_user = (role == "user")
        
        # ── 1. Specialized News Rendering ───────────────────────────
        if role == "bot" and text.startswith("NEWS_DATA|"):
            self._add_news_cards(text)
            self._chat.insert("end", "\n")
            self._smart_scroll()
            self._chat.configure(state="disabled")
            # Bubbles computed parameters back to caller functions
            return

        # ── 2. Specialized Stock Rendering ──────────────────────────
        if role == "bot" and text.startswith("STOCK_DATA|"):
            self._add_stock_card(text)
            self._chat.insert("end", "\n")
            self._smart_scroll()
            self._chat.configure(state="disabled")
            # Bubbles computed parameters back to caller functions
            return

        # ── 3. Specialized Weather Rendering ────────────────────────
        if role == "bot" and text.startswith("WEATHER_DATA|"):
            self._add_weather_card(text)
            self._chat.insert("end", "\n")
            self._smart_scroll()
            self._chat.configure(state="disabled")
            # Bubbles computed parameters back to caller functions
            return

        # ── 4. Specialized System Rendering ─────────────────────────
        if role == "bot" and text.startswith("SYS_DATA|"):
            self._add_sys_card(text)
            self._chat.insert("end", "\n")
            self._smart_scroll()
            self._chat.configure(state="disabled")
            # Bubbles computed parameters back to caller functions
            return

        # ── 5. Specialized SOS Rendering ────────────────────────────
        if role == "bot" and text.startswith("SOS_DATA|"):
            self._add_sos_card(text)
            self._chat.insert("end", "\n")
            self.after(50, lambda: self._chat.see("end"))
            self._chat.configure(state="disabled")
            # Bubbles computed parameters back to caller functions
            return
            
        # ── 6. Specialized Reminder Rendering ──────────────────────
        if role == "bot" and text.startswith("REMINDER_DATA|"):
            self._add_reminder_card(text)
            self._chat.insert("end", "\n")
            self._smart_scroll()
            self._chat.configure(state="disabled")
            # Bubbles computed parameters back to caller functions
            return

        # ── 7. Specialized Alarm Rendering ─────────────────────────
        if role == "bot" and text.startswith("ALARM_DATA|"):
            self._add_alarm_card(text)
            self._chat.insert("end", "\n")
            self._smart_scroll()
            self._chat.configure(state="disabled")
            # Bubbles computed parameters back to caller functions
            return

        # ── 5. Standard Bubble Rendering ───────────────────────────
        # Use themed colors for light mode, but restore distinct dark bubbles for dark mode
        is_dark = (BG == "#000000")
        if is_dark:
            bubble_bg = "#151515" if is_user else "#0a0a0a"
            bubble_outline = GREEN if is_user else "#ffffff"
        else:
            bubble_bg = BG4 if is_user else BG3
            bubble_outline = TEAL if is_user else BORDER

        # The Bubble Frame (Rounded with themed border)
        bubble = RoundedFrame(self._chat, radius=15, bg=bubble_bg, outline=bubble_outline, border_width=1)
        bubble._is_user_bubble = is_user

        # Message Text
        msg_lbl = tk.Label(bubble, text=text, bg=bubble_bg, fg=TEAL2 if is_user else TEXT,
                           font=("Segoe UI", 10), wraplength=350, justify="left")
        msg_lbl.pack(anchor="w", padx=12, pady=(8, 0))
        
        # Timestamp
        time_lbl = tk.Label(bubble, text=ts, bg=bubble_bg, fg=TEXT2,
                            font=("Segoe UI", 7))
        time_lbl.pack(anchor="e", padx=12, pady=(0, 6))

        self._enable_bubble_scrolling(bubble)

        # Insert into text widget with native tag alignment
        tag_name = "user" if is_user else "bot"
        start_idx = self._chat.index("end-1c")
        
        self._chat.window_create("end", window=bubble, padx=15, pady=5)
        self._chat.insert("end", "\n")
        
        self._chat.tag_add(tag_name, start_idx, "end-1c")
        
        self._smart_scroll()
        self._chat.configure(state="disabled")

    def _add_news_cards(self, data_str: str):
        """Renders structured news data into stylized cards."""
        # Safety guard intercepting unexpected GUI or network anomalies
        try:
            parts = data_str.split("||")
            header = parts[0].split("|")  # ["NEWS_DATA", "Category"]
            category = header[1] if len(header) > 1 else "News"
            
            container = tk.Frame(self._chat, bg=BG, padx=10, pady=5)
            
            # Header
            hdr_frame = tk.Frame(container, bg=BG)
            hdr_frame.pack(fill="x", pady=(0, 6))
            label(hdr_frame, text=f"Latest {category} Headlines", 
                  bg=BG, fg=GOLD, font=FONT_MD).pack(side="left")

            for item in parts[1:]:
                fields = item.split("|")
                if len(fields) < 3: continue
                title, source, url = fields
                
                # Card container from theme.py
                outer, inner = card(container, bg=BG3, pady=6)
                outer.pack(fill="x", pady=6)
                
                # Headline Title
                label(inner, text=title, bg=BG3, fg=TEXT, 
                      font=("Segoe UI", 10, "bold"), 
                      wraplength=340, justify="left").pack(anchor="w")
                
                # Footer row: Source + Read More
                footer = frame(inner, bg=BG3)
                footer.pack(fill="x", pady=(8, 0))
                
                label(footer, text=f"via {source}", bg=BG3, fg=TEXT2, font=FONT_SM).pack(side="left")
                
                # 'Read More' as a flat teal link-style button
                btn = tk.Button(footer, text="Read More ↗", bg=BG3, fg=TEAL2, font=FONT_SM,
                                relief="flat", bd=0, cursor="hand2", activebackground=BG3,
                                command=lambda u=url: webbrowser.open(u))
                btn.pack(side="right")
                
                # Hover effect for link
                btn.bind("<Enter>", lambda e, b=btn: b.config(fg=TEAL))
                btn.bind("<Leave>", lambda e, b=btn: b.config(fg=TEAL2))

            # Insert into Text widget
            self._chat.window_create("end", window=container)
            
        # Recovers control silently from thread interruptions or window disposal errors
        except Exception as e:
            # Fallback for parsing errors
            self._chat.insert("end", f"Error rendering news: {e}", "error")

    def _add_stock_card(self, data_str: str):
        """Renders structured stock data into a beautiful card."""
        # Safety guard intercepting unexpected GUI or network anomalies
        try:
            fields = data_str.split("|")
            if len(fields) < 5: return
            name, symbol, price, currency = fields[1], fields[2], fields[3], fields[4]
            
            container = tk.Frame(self._chat, bg=BG, padx=15, pady=8)
            self._enable_bubble_scrolling(container)
            
            # Card container from theme.py
            outer, inner = card(container, bg=BG3, pady=12)
            outer.pack(fill="x")
            
            # Header Row: Name & Symbol
            hdr = frame(inner, bg=BG3)
            hdr.pack(fill="x")
            label(hdr, text=name, bg=BG3, fg=TEXT, font=("Segoe UI", 11, "bold")).pack(side="left")
            label(hdr, text=f"({symbol})", bg=BG3, fg=TEXT2, font=FONT_SM).pack(side="left", padx=6)
            
            label(inner, text="MARKET PRICE", bg=BG3, fg=TEXT2, font=FONT_CAPS).pack(anchor="w", pady=(10, 0))
            
            # Price Row: Big Price
            price_row = frame(inner, bg=BG3)
            price_row.pack(fill="x", pady=(2, 0))
            
            label(price_row, text=f"{currency} ", bg=BG3, fg=GOLD, font=("Segoe UI", 12, "bold")).pack(side="left", pady=(5, 0))
            label(price_row, text=price, bg=BG3, fg=TEAL2, font=("Segoe UI", 24, "bold")).pack(side="left")
            
            # Footer / Live indicator
            footer = frame(inner, bg=BG3)
            footer.pack(fill="x", pady=(10, 0))
            
            dot_c = tk.Canvas(footer, bg=BG3, width=8, height=8, bd=0, highlightthickness=0)
            dot_c.pack(side="left", pady=4)
            dot_c.create_oval(1, 1, 7, 7, fill=GREEN, outline="")
            label(footer, text="Live Market Data — Relayed", bg=BG3, fg=TEXT2, font=("Segoe UI", 7, "italic")).pack(side="left", padx=4)

            self._enable_bubble_scrolling(container)
            # Insert into Text widget
            self._chat.window_create("end", window=container)
            
        # Recovers control silently from thread interruptions or window disposal errors
        except Exception as e:
            self._chat.insert("end", f"Error rendering stock: {e}", "error")

    def _add_weather_card(self, data_str: str):
        """Renders structured weather data into a beautiful card."""
        # Safety guard intercepting unexpected GUI or network anomalies
        try:
            fields = data_str.split("|")
            if len(fields) < 6: return
            city, temp, desc, hum, wind = fields[1:]
            
            container = tk.Frame(self._chat, bg=BG, padx=15, pady=8)
            self._enable_bubble_scrolling(container)
            
            # Card container from theme.py
            outer, inner = card(container, bg=BG3, pady=12)
            outer.pack(fill="x")
            
            # Header Row: City
            hdr = frame(inner, bg=BG3)
            hdr.pack(fill="x")
            label(hdr, text=city, bg=BG3, fg=TEXT, font=("Segoe UI", 12, "bold")).pack(side="left")
            label(hdr, text="CURRENT WEATHER", bg=BG3, fg=TEXT2, font=FONT_CAPS).pack(side="right", pady=2)
            
            # Main Info: Temp & Description
            main_row = frame(inner, bg=BG3)
            main_row.pack(fill="x", pady=(10, 0))
            
            label(main_row, text=f"{temp}°C", bg=BG3, fg=TEAL, font=("Segoe UI", 28, "bold")).pack(side="left")
            label(main_row, text=desc, bg=BG3, fg=TEXT, font=("Segoe UI", 11, "italic")).pack(side="left", padx=15, pady=(8, 0))
            
            separator(inner).pack(fill="x", pady=12)
            
            # Stats Row: Humidity & Wind
            stats = frame(inner, bg=BG3)
            stats.pack(fill="x")
            
            # Humidity
            h_box = frame(stats, bg=BG3)
            h_box.pack(side="left", expand=True)
            label(h_box, text="HUMIDITY", bg=BG3, fg=TEXT2, font=FONT_CAPS).pack()
            label(h_box, text=f"{hum}%", bg=BG3, fg=BLUE, font=("Segoe UI", 10, "bold")).pack()
            
            # Wind
            w_box = frame(stats, bg=BG3)
            w_box.pack(side="left", expand=True)
            label(w_box, text="WIND SPEED", bg=BG3, fg=TEXT2, font=FONT_CAPS).pack()
            label(w_box, text=f"{wind} km/h", bg=BG3, fg=GREEN, font=("Segoe UI", 10, "bold")).pack()

            self._enable_bubble_scrolling(container)
            # Insert into Text widget
            self._chat.window_create("end", window=container)
            
        # Recovers control silently from thread interruptions or window disposal errors
        except Exception as e:
            self._chat.insert("end", f"Error rendering weather: {e}", "error")

    def _add_sys_card(self, data_str: str):
        """Renders structured system telemetry into a beautiful card."""
        # Safety guard intercepting unexpected GUI or network anomalies
        try:
            f = data_str.split("|")
            if len(f) < 10: return
            cpu_p, ram_u, ram_t, ram_p, disk_u, disk_t, disk_p, bat, plug = f[1:]
            
            container = tk.Frame(self._chat, bg=BG, padx=15, pady=8)
            self._enable_bubble_scrolling(container)
            
            # Card container from theme.py
            outer, inner = card(container, bg=BG3, pady=12)
            outer.pack(fill="x")
            
            # Header Row
            hdr = frame(inner, bg=BG3)
            hdr.pack(fill="x", pady=(0, 10))
            label(hdr, text="SYSTEM TELEMETRY", bg=BG3, fg=GOLD, font=FONT_CAPS).pack(side="left")
            label(hdr, text="REAL-TIME", bg=BG3, fg=TEXT2, font=("Segoe UI", 7, "bold")).pack(side="right")
            
            # Resource Rows Helper
            def add_row(parent, name, val, pct, color):
                row = frame(parent, bg=BG3)
                row.pack(fill="x", pady=2)
                label(row, text=name, bg=BG3, fg=TEXT, font=FONT_SM).pack(side="left")
                label(row, text=val, bg=BG3, fg=color, font=FONT_SM).pack(side="right")
                
                bar_bg = tk.Frame(parent, bg=BORDER, height=4)
                bar_bg.pack(fill="x", pady=(0, 6))
                bar_fill = tk.Frame(bar_bg, bg=color, height=4)
                # Safety guard intercepting unexpected GUI or network anomalies
                try:
                    rel_w = float(pct) / 100
                except:
                    rel_w = 0
                bar_fill.place(x=0, y=0, relheight=1, relwidth=rel_w)

            add_row(inner, "Processor (CPU)", f"{cpu_p}%", cpu_p, GREEN)
            add_row(inner, "Memory (RAM)", f"{ram_u} / {ram_t} GB", ram_p, TEAL)
            add_row(inner, "Storage (Disk)", f"{disk_u} / {disk_t} GB", disk_p, BLUE)
            
            # Battery Row (if applicable)
            if bat != 'N':
                separator(inner).pack(fill="x", pady=8)
                b_row = frame(inner, bg=BG3)
                b_row.pack(fill="x")
                p_text = "Charging" if plug == '1' else "On Battery"
                label(b_row, text=f"Battery Status: {bat}%", bg=BG3, fg=TEXT, font=FONT_SM).pack(side="left")
                label(b_row, text=p_text, bg=BG3, fg=GOLD, font=FONT_SM).pack(side="right")

            self._enable_bubble_scrolling(container)
            # Insert into Text widget
            self._chat.window_create("end", window=container)
            
        # Recovers control silently from thread interruptions or window disposal errors
        except Exception as e:
            self._chat.insert("end", f"Error rendering system info: {e}", "error")

    def _add_sos_card(self, data_str: str):
        """Renders critical SOS alert info into a premium emergency card."""
        # Safety guard intercepting unexpected GUI or network anomalies
        try:
            f = data_str.split("|")
            if len(f) < 4: return
            loc, contact, ts = f[1:]
            
            container = tk.Frame(self._chat, bg=BG, padx=15, pady=12)
            
            # Use red border for emergency (Rounded)
            outer = RoundedFrame(container, radius=12, bg=RED)
            inner = tk.Frame(outer, bg=BG3)
            inner.pack(fill="both", expand=True, padx=2, pady=2, ipadx=15, ipady=15)
            outer.pack(fill="x")
            
            # Header with Pulse Indicator
            hdr = frame(inner, bg=BG3)
            hdr.pack(fill="x", pady=(0, 10))
            
            dot_c = tk.Canvas(hdr, bg=BG3, width=12, height=12, bd=0, highlightthickness=0)
            dot_c.pack(side="left", pady=2)
            dot_c.create_oval(2, 2, 10, 10, fill=RED, outline="")
            
            label(hdr, text="EMERGENCY ALERT TRIGGERED", bg=BG3, fg=RED, font=("Segoe UI", 11, "bold")).pack(side="left", padx=8)
            label(hdr, text=ts, bg=BG3, fg=TEXT2, font=FONT_SM).pack(side="right")
            
            separator(inner).pack(fill="x", pady=8)
            
            # Info Rows
            def add_field(parent, icon, title, val, color=TEXT):
                row = frame(parent, bg=BG3)
                row.pack(fill="x", pady=4)
                label(row, text=icon, bg=BG3, fg=GOLD, font=("Segoe UI", 11)).pack(side="left")
                label(row, text=f" {title}:", bg=BG3, fg=TEXT2, font=FONT_SM).pack(side="left")
                label(row, text=val, bg=BG3, fg=color, font=("Segoe UI", 10, "bold")).pack(side="left", padx=5)

            add_field(inner, "📍", "Detected Location", loc, TEAL)
            add_field(inner, "📞", "Notified Contact", contact, GOLD)
            
            # Status Footer
            footer = frame(inner, bg=BG3)
            footer.pack(fill="x", pady=(15, 0))
            label(footer, text="Help is on the way. Please stay calm.", bg=BG3, fg=TEXT2, font=("Segoe UI", 9, "italic")).pack(side="left")
            label(footer, text="SENT ✔", bg=BG3, fg=GREEN, font=FONT_CAPS).pack(side="right")

            self._enable_bubble_scrolling(container)
            # Insert into Text widget
            self._chat.window_create("end", window=container)
            
        # Recovers control silently from thread interruptions or window disposal errors
        except Exception as e:
            self._chat.insert("end", f"Error rendering SOS card: {e}", "error")

    def _add_reminder_card(self, data_str: str):
        """Renders a premium reminder card."""
        # Safety guard intercepting unexpected GUI or network anomalies
        try:
            parts = data_str.split("|")
            if len(parts) < 3: return
            task, ts = parts[1], parts[2]
            
            container = tk.Frame(self._chat, bg=BG, padx=15, pady=8)
            outer, inner = card(container, bg=BG3, pady=12)
            outer.pack(fill="x")
            
            hdr = frame(inner, bg=BG3)
            hdr.pack(fill="x", pady=(0, 8))
            label(hdr, text="🔔  REMINDER", bg=BG3, fg=TEAL2, font=("Segoe UI", 10, "bold")).pack(side="left")
            label(hdr, text=ts, bg=BG3, fg=TEXT2, font=FONT_SM).pack(side="right")
            
            separator(inner).pack(fill="x", pady=8)
            
            label(inner, text=task, bg=BG3, fg=TEXT, font=("Segoe UI", 12, "bold"), 
                  wraplength=340, justify="left").pack(anchor="w", pady=5)
            
            footer = frame(inner, bg=BG3)
            footer.pack(fill="x", pady=(10, 0))
            label(footer, text="Scheduled Task Triggered", bg=BG3, fg=TEXT2, font=("Segoe UI", 8, "italic")).pack(side="left")
            
            self._enable_bubble_scrolling(container)
            self._chat.window_create("end", window=container)
        # Recovers control silently from thread interruptions or window disposal errors
        except Exception as e:
            self._chat.insert("end", f"Error rendering reminder: {e}", "error")

    def _add_alarm_card(self, data_str: str):
        """Renders a premium alarm card."""
        # Safety guard intercepting unexpected GUI or network anomalies
        try:
            parts = data_str.split("|")
            ts = parts[1] if len(parts) > 1 else "--:--"
            
            container = tk.Frame(self._chat, bg=BG, padx=15, pady=8)
            outer, inner = card(container, bg=BG3, pady=12)
            outer.config(highlightbackground=GOLD, highlightthickness=1)
            outer.pack(fill="x")
            
            hdr = frame(inner, bg=BG3)
            hdr.pack(fill="x", pady=(0, 8))
            label(hdr, text="⏰  ALARM", bg=BG3, fg=GOLD, font=("Segoe UI", 10, "bold")).pack(side="left")
            label(hdr, text=ts, bg=BG3, fg=TEXT2, font=FONT_SM).pack(side="right")
            
            label(inner, text="Time's Up!", bg=BG3, fg=TEXT, font=("Segoe UI", 16, "bold")).pack(pady=10)
            
            self._enable_bubble_scrolling(container)
            self._chat.window_create("end", window=container)
        # Recovers control silently from thread interruptions or window disposal errors
        except Exception as e:
            self._chat.insert("end", f"Error rendering alarm: {e}", "error")

    # ── Inline Settings: Public API ───────────────────────────────────────────

    def show_settings(self, section: str = "profile"):
        """Switch from chat view to the inline settings panel."""
        # Safety guard intercepting unexpected GUI or network anomalies
        try:
            self._chat_area.pack_forget()
            self._settings_area.pack(fill="both", expand=True)
            self._settings_show_section(section)
        except tk.TclError:
            pass

    def _close_settings(self):
        """Switch back to the chat view."""
        # Safety guard intercepting unexpected GUI or network anomalies
        try:
            self._settings_area.pack_forget()
            self._chat_area.pack(fill="both", expand=True)
        except tk.TclError:
            pass

    def _settings_show_section(self, section: str):
        """Highlight active tab and render the correct settings section."""
        for s, btn in self._settings_nav_btns.items():
            btn.configure(
                bg=BG3   if s == section else BG4,
                fg=TEAL2 if s == section else TEXT2
            )
        # Clear old content
        # Safety guard intercepting unexpected GUI or network anomalies
        try:
            for w in self._settings_content.winfo_children():
                w.destroy()
        except tk.TclError:
            # Bubbles computed parameters back to caller functions
            return

        if section == "profile":
            self._settings_build_profile()
        elif section == "how_to_use":
            self._settings_build_howto()
        elif section == "usage_guide":
            self._settings_build_usage()

    def _settings_build_usage(self):
        """Builds a detailed usage guide for shortcuts and buttons."""
        p = self._settings_content
        
        def add_heading(text):
            label(p, text=text, bg=BG2, fg=TEAL2, font=FONT_MD).pack(anchor="w", padx=20, pady=(18, 8))
            separator(p).pack(fill="x", padx=20, pady=(0, 10))

        def add_item(title, desc, icon="•"):
            row = tk.Frame(p, bg=BORDER)
            row.pack(fill="x", padx=20, pady=3)
            inner_row = frame(row, bg=BG3)
            inner_row.pack(fill="both", expand=True, padx=1, pady=1, ipadx=10, ipady=8)
            
            label(inner_row, text=f"{icon}  {title}", bg=BG3, fg=TEXT, font=("Segoe UI", 10, "bold")).pack(side="left", padx=5)
            label(inner_row, text=desc, bg=BG3, fg=TEXT2, font=FONT_SM).pack(side="right", padx=10)

        # ── 1. Voice Control Shortcuts ────────────────
        add_heading("🎤  VOICE CONTROL SHORTCUTS")
        add_item("Alt + B + Space", "Turn Microphone ON (Global)")
        add_item("Alt + N + Space", "Turn Microphone OFF (Global)")
        label(p, text="Note: Global shortcuts work even when the app is minimized.", 
              bg=BG2, fg=TEXT2, font=("Segoe UI", 8, "italic")).pack(anchor="w", padx=25, pady=(2, 10))

        # ── 2. Services Buttons ─────────────────────
        add_heading("⚡  SERVICES BUTTONS")
        add_item("Emergency SOS", "Triggers immediate alert to contacts", "⚠")
        add_item("Local Weather", "Updates weather for your profile city", "🌤")
        add_item("Latest News", "Fetches top global news headlines", "📰")
        add_item("Stock Market", "Checks real-time market indices", "📈")

        # ── 3. Quick Action Buttons ────────────────
        add_heading("🚀  QUICK ACTION BUTTONS")
        add_item("Settings (⚙)", "Opens this configuration panel")
        add_item("Chrome (🌐)", "Launches Google Chrome browser")
        add_item("Calculator (🖩)", "Opens Windows Calculator")
        add_item("Logout (⏻)", "Sign out and return to login screen")
        
        # Bottom spacer
        frame(p, bg=BG2, height=30).pack()






    # ── Settings: Theme ───────────────────────────────────────────────────────

    def _settings_build_theme(self):
        p = self._settings_content
        label(p, text="Appearance", bg=BG2, fg=TEXT,
              font=FONT_LG).pack(anchor="w", padx=20, pady=(16, 12))
        label(p, text="Current theme: Dark (default)", bg=BG2,
              fg=TEXT2, font=FONT_SM).pack(anchor="w", padx=20, pady=(0, 12))

        for name, active in [("🌑  Dark (Default)", True),
                              ("☀️  Light",          False),
                              ("🟢  Teal Accent",    False)]:
            row = frame(p, bg=BG3)
            row.pack(fill="x", padx=20, pady=3, ipady=6, ipadx=10)
            label(row, text=name, bg=BG3,
                  fg=TEAL2 if active else TEXT2,
                  font=FONT_SM).pack(side="left", padx=10)
            if active:
                label(row, text="✓ Active", bg=BG3,
                      fg=GREEN, font=FONT_SM).pack(side="right", padx=10)

        label(p, text="More themes coming in future updates.",
              bg=BG2, fg=BORDER, font=FONT_SM).pack(anchor="w", padx=20, pady=(16, 12))

    # ── Settings: Profile ─────────────────────────────────────────────────────

    def _settings_build_profile(self):
        p = self._settings_content
        label(p, text="Your Profile", bg=BG2, fg=TEXT,
              font=FONT_LG).pack(anchor="w", padx=20, pady=(16, 12))

        self._settings_profile_lbl = label(p, text="Loading profile…",
                                           bg=BG2, fg=TEXT2, font=FONT_SM)
        self._settings_profile_lbl.pack(anchor="w", padx=20)

        # Imports threading libraries to execute non-blocking updates loops
        import threading
        threading.Thread(target=self._settings_load_profile, daemon=True).start()

    def _settings_load_profile(self):
        if not self.api:
            self.after(0, self._settings_profile_no_api)
            # Bubbles computed parameters back to caller functions
            return
        res = self.api.get_profile()
        self.after(0, self._settings_render_profile, res)

    def _settings_profile_no_api(self):
        # Safety guard intercepting unexpected GUI or network anomalies
        try:
            self._settings_profile_lbl.configure(text="API client not available.")
        # Recovers control silently from thread interruptions or window disposal errors
        except (tk.TclError, AttributeError):
            pass

    def _settings_render_profile(self, res):
        # Safety guard intercepting unexpected GUI or network anomalies
        try:
            if not self._settings_content.winfo_exists():
                # Bubbles computed parameters back to caller functions
                return
            for w in self._settings_content.winfo_children():
                w.destroy()

            p = self._settings_content
            label(p, text="Your Profile", bg=BG2, fg=TEXT,
                  font=FONT_LG).pack(anchor="w", padx=20, pady=(16, 12))

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
                    row.pack(fill="x", padx=20, pady=3)
                    inner_row = frame(row, bg=BG3)
                    inner_row.pack(fill="both", expand=True, padx=1, pady=1, ipadx=10, ipady=7)
                    
                    label(inner_row, text=key, bg=BG3, fg=TEXT2,
                          font=FONT_SM).pack(side="left", padx=10)
                    label(inner_row, text=str(val), bg=BG3, fg=TEXT,
                          font=FONT_SM).pack(side="right", padx=10)
            else:
                label(p, text=f"Could not load profile: {res.get('message')}",
                      bg=BG2, fg=RED, font=FONT_SM).pack(anchor="w", padx=20)
        # Recovers control silently from thread interruptions or window disposal errors
        except (tk.TclError, RuntimeError, AttributeError):
            pass

    # ── Settings: How to Use ──────────────────────────────────────────────────

    def _settings_build_howto(self):
        """Renders the how-to guide directly onto the scrollable content area."""
        p = self._settings_content
        
        label(p, text="How to Use", bg=BG2, fg=TEXT,
              font=FONT_LG).pack(anchor="w", padx=20, pady=(16, 10))

        def add_section(title, content):
            # Section Header
            hdr = frame(p, bg=BG2)
            hdr.pack(fill="x", padx=20, pady=(15, 5))
            label(hdr, text=title, bg=BG2, fg=TEAL2, font=("Segoe UI", 10, "bold")).pack(side="left")
            separator(p).pack(fill="x", padx=20, pady=(0, 10))
    
            # Content
            txt_frame = frame(p, bg=BG3)
            txt_frame.pack(fill="x", padx=20, pady=2, ipadx=10, ipady=10)
            
            # We split by line to add bullet points or clean spacing
            for line in content.strip().split("\n"):
                lbl = tk.Label(txt_frame, text=line, bg=BG3, fg=TEXT, font=FONT_SM,
                               anchor="w", justify="left", wraplength=480)
                lbl.pack(fill="x", pady=1)

        # ── 1. Voice Control ────────────────
        add_section("🎤  VOICE COMMANDS", 
            "1. Click the MIC button in the toolbar to toggle on/off.\n"
            "2. When the orb glows,it's listening.\n"
            "3. Speak clearly—Application will transcribe your words.\n"
            "4. AI will speak back and show the reply in chat.")

        # ── 2. Text Commands ────────────────
        add_section("⌨  TEXT COMMANDS",
            "Type any command in the input box and press Enter or click send button")

        # ── 3. Example Commands ─────────────
        add_section("📋  EXAMPLE COMMANDS",
            "• \"What time is it?\"\n"
            "• \"Weather in Mumbai\"\n"
            "• \"Open Chrome\"\n"
            "• \"Set timer for 5 minutes\"\n"
            "• \"Latest technology news\"\n"
            "• \"Stock price of RELIANCE\"\n"
            "• \"SOS\" or \"Emergency\"")

        # ── 4. Toolbar ──────────────────────
        add_section("🔧  SMARTBAR",
            "• MIC: Toggle microphone\n"
            "• ▼ / ▲: Expand/Collapse window\n"
            "• ⚙: Open settings\n"
            "• ✕: Exit application\n"
            "• Tip: Drag the toolbar to move the window.")

        # ── 5. AI Fallback ──────────────────
        add_section("🧠  AI FALLBACK",
            " commands are responed by AI.")

        # ── 6. SOS ──────────────────────────
        add_section("🆘  SOS",
            "Say 'SOS' or click the red button to alert emergency contacts.")

        # Bottom spacer
        frame(p, bg=BG2, height=30).pack()
