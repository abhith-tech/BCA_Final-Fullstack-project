# ============================================================
#  EmpowerAccess Desktop — ui/login_window.py
#  Two-panel login screen — left design, right form
# ============================================================

# Imports standard Tkinter toolkit to manage window elements
import tkinter as tk
# Imports threading libraries to execute non-blocking updates loops
import threading
# Imports math routines to calculate orbital rotation angles and sine waves
import math
# Imports time package to compute animations delays and clock formats
import time
# Imports thread-safe queue routines to pass login verification structures
import queue

from config import APP_NAME, APP_SUBTITLE, APP_MOTTO, MAIN_W, MAIN_H
from ui.theme import *


# Two-panel entry credentials frame blocking interaction with parent forms
class LoginWindow(tk.Toplevel):
    """
    Standalone login window.
    on_success(token, name, role) called after successful login.
    """

    def __init__(self, master, api_client, on_success):
        super().__init__(master)
        self.api        = api_client
        self.on_success = on_success

        self.title(f"{APP_NAME} · Sign In")
        self.configure(bg=BG)
        self.resizable(False, False)

        WIN_W, WIN_H = 780, 650
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x  = (sw - WIN_W) // 2
        y  = (sh - WIN_H) // 2
        self.geometry(f"{WIN_W}x{WIN_H}+{x}+{y}")
        self.overrideredirect(True)
        self.update_idletasks()
        set_rounded_corners(self)

        self._orb_angle = 0.0
        self._orb_pulse = 0.0
        # self._particles removed for concentric design

        self._build()
        self._start_orb_animation()
        self.grab_set()

    # ── Layout ────────────────────────────────────────────────────────────────

    def _build(self):
        root_frame = frame(self, bg=BG2)
        root_frame.pack(fill="both", expand=True, padx=1, pady=1)

        # ── Left panel ────────────────────────────────────────────────────
        self.left = frame(root_frame, bg="#000000")
        self.left.place(x=0, y=0, width=380, height=648)

        # Canvas for animated orb
        self.orb_canvas = tk.Canvas(self.left, bg="#000000", bd=0,
                                     highlightthickness=0, width=380, height=280)
        self.orb_canvas.pack(pady=(100, 0))

        # Feature list
        feats = [
            "Voice + Text command engine",
            "Whisper STT  |  ElevenLabs TTS",
            "Real-time weather, news & stocks",
            "Emergency SOS with SMS alerts",
            "Gemini AI fallback assistant",
        ]
        for f_text in feats:
            row = frame(self.left, bg="#000000")
            row.pack(fill="x", padx=32, pady=2)
            tk.Canvas(row, bg="#000000", width=7, height=7,
                      bd=0, highlightthickness=0).pack(side="left", padx=(0, 8))
            # teal dot
            dot_c = tk.Canvas(row, bg="#000000", width=7, height=7,
                               bd=0, highlightthickness=0)
            dot_c.pack(side="left", padx=(0, 8))
            dot_c.create_oval(1, 1, 6, 6, fill=TEAL2, outline="")
            label(row, text=f_text, bg="#000000",
                  fg="rgba(255,255,255,0.6)" if False else "#7a9ab0",
                  font=FONT_SM).pack(side="left")

        tagline = label(self.left,
                        text="AI-Powered Accessibility Platform",
                        bg="#000000", fg=TEAL2, font=FONT_SM)
        tagline.pack(pady=(14, 0))

        # ── Vertical divider ──────────────────────────────────────────────
        tk.Frame(root_frame, bg=BORDER, width=1).place(x=380, y=0, width=1, height=648)

        # ── Right panel ───────────────────────────────────────────────────
        right = frame(root_frame, bg=BG2)
        right.place(x=381, y=0, width=399, height=648)

        # Header
        hdr = frame(right, bg=BG2)
        hdr.pack(fill="x", padx=32, pady=(100, 24))

        # Close button for borderless window
        close_btn = button(right, text="✕", command=self.master.destroy, bg=BG2, fg=TEXT2, font=("Segoe UI", 12), hover_bg=RED)
        close_btn.place(x=365, y=12, width=24, height=24)

        badge = tk.Canvas(hdr, bg=BG3, width=44, height=44, bd=0,
                          highlightthickness=1, highlightbackground=BORDER)
        badge.pack(side="left", padx=(0, 14))
        badge.create_text(22, 22, text="EA", fill=TEAL2,
                          font=("Segoe UI", 13, "bold"))

        title_wrap = frame(hdr, bg=BG2)
        title_wrap.pack(side="left")
        label(title_wrap, text=APP_NAME, bg=BG2, fg=TEXT,
              font=("Segoe UI", 16, "bold")).pack(anchor="w")
        label(title_wrap, text=APP_SUBTITLE, bg=BG2, fg=TEXT2,
              font=FONT_SM).pack(anchor="w")

        # Form
        form = frame(right, bg=BG2)
        form.pack(fill="x", padx=32)

        label(form, text="Username or email", bg=BG2, fg=TEXT2,
              font=FONT_CAPS).pack(anchor="w", pady=(0, 4))
        self.email_var = tk.StringVar()
        email_e = entry(form, textvariable=self.email_var, font=FONT)
        email_e.pack(fill="x", ipady=8, pady=(0, 16))
        email_e.bind("<Return>", lambda e: self.pwd_entry.focus())

        label(form, text="Password", bg=BG2, fg=TEXT2,
              font=FONT_CAPS).pack(anchor="w", pady=(0, 4))
        self.pwd_var = tk.StringVar()
        self.pwd_entry = entry(form, textvariable=self.pwd_var,
                               show="•", font=FONT)
        self.pwd_entry.pack(fill="x", ipady=8, pady=(0, 20))
        self.pwd_entry.bind("<Return>", lambda e: self._do_login())

        self.login_btn = teal_button(form, text="LOGIN",
                                     command=self._do_login,
                                     font=("Segoe UI", 11, "bold"))
        self.login_btn.pack(fill="x", ipady=9)

        # Status
        self.status_var = tk.StringVar(value="Please login")
        label(form, textvariable=self.status_var, bg=BG2, fg=TEXT2,
              font=FONT_SM).pack(pady=(10, 4))

        # Session info row
        sess_row = frame(form, bg=BG2)
        sess_row.pack()
        dot = tk.Canvas(sess_row, bg=BG2, width=8, height=8, bd=0,
                        highlightthickness=0)
        dot.pack(side="left", padx=(0, 5))
        dot.create_oval(1, 1, 7, 7, fill=GREEN, outline="")
        label(sess_row, text="Session expires in 8 hrs", bg=BG2,
              fg=TEXT2, font=FONT_SM).pack(side="left")

        # Motto
        label(form, text=APP_MOTTO, bg=BG2, fg=BORDER,
              font=("Segoe UI", 9, "italic")).pack(pady=(16, 0))

        email_e.focus()

    # ── Orb animation ─────────────────────────────────────────────────────────

    # Triggers recurrent canvas redraw tasks every 33 milliseconds
    def _start_orb_animation(self):
        self._orb_angle = 0.0
        self._orb_pulse = 0.0
        self._animate_orb()

    # Animates concentric glowing arcs and central pulsar pulses on local canvas
    def _animate_orb(self):
        # Safety guard intercepting unexpected GUI or network anomalies
        try:
            c = self.orb_canvas
            c.delete("all")
            W, H = 380, 280
            cx, cy = W // 2, H // 2

            self._orb_angle += 0.02
            self._orb_pulse = (math.sin(time.time() * 2.0) + 1) / 2
            scale = 1.0 + (0.04 * self._orb_pulse)

            # 1. Aura bloom (Minimal)
            c.create_oval(cx - 85, cy - 85, cx + 85, cy + 85,
                          fill="#000000", outline="")

            # 2. Outer Rotating Arcs
            angle_a = math.degrees(self._orb_angle)
            r_a = int(72 * scale)
            c.create_arc(cx - r_a, cy - r_a, cx + r_a, cy + r_a,
                         start=angle_a, extent=100, outline=TEAL2, 
                         style="arc", width=2)
            c.create_arc(cx - r_a, cy - r_a, cx + r_a, cy + r_a,
                         start=angle_a + 120, extent=100, outline=TEAL2, 
                         style="arc", width=2)
            c.create_arc(cx - r_a, cy - r_a, cx + r_a, cy + r_a,
                         start=angle_a + 240, extent=100, outline=TEAL2, 
                         style="arc", width=2)

            # 3. Middle Rotating Arcs (Counter)
            angle_b = math.degrees(-self._orb_angle * 1.8)
            r_b = int(62 * scale)
            c.create_arc(cx - r_b, cy - r_b, cx + r_b, cy + r_b,
                         start=angle_b, extent=150, outline=TEAL, 
                         style="arc", width=1)
            c.create_arc(cx - r_b, cy - r_b, cx + r_b, cy + r_b,
                         start=angle_b + 180, extent=150, outline=TEAL, 
                         style="arc", width=1)

            # 4. Central Solid Core
            core_r = int(32 * scale)
            c.create_oval(cx - core_r, cy - core_r, cx + core_r, cy + core_r,
                          fill="#0a1a24", outline=TEAL2, width=2)
            
            # Subtle Pulsar
            p_r = int(18 * (0.9 + 0.1 * math.sin(time.time() * 3)))
            c.create_oval(cx - p_r, cy - p_r, cx + p_r, cy + p_r,
                          fill="#123440", outline="")

            # 5. Highlight
            c.create_oval(cx - 14, cy - 20, cx + 2, cy - 6,
                          fill="#1c3d52", outline="")

            self.after(33, self._animate_orb)
        except tk.TclError:
            pass

    # ── Login action ──────────────────────────────────────────────────────────

    # Spawns async worker thread verification loops checking user login fields
    def _do_login(self):
        email = self.email_var.get().strip()
        pwd   = self.pwd_var.get().strip()

        if not email or not pwd:
            self._set_status("Please enter email and password.", RED)
            # Bubbles computed parameters back to caller functions
            return

        self.login_btn.configure(text="Logging in...", state="disabled")
        self._set_status("Authenticating...", TEAL2)

        self._login_queue = queue.Queue()
        threading.Thread(target=self._login_thread,
                         args=(email, pwd), daemon=True).start()
        self._check_login_queue()

    def _login_thread(self, email, pwd):
        res = self.api.login(email, pwd)
        self._login_queue.put(res)

    def _check_login_queue(self):
        # Safety guard intercepting unexpected GUI or network anomalies
        try:
            res = self._login_queue.get_nowait()
            self._handle_login_result(res)
        except queue.Empty:
            self.after(100, self._check_login_queue)

    def _handle_login_result(self, res):
        self.login_btn.configure(text="LOGIN", state="normal")
        if res.get("success"):
            self._set_status(f"Welcome, {res.get('name')}!", GREEN)
            self.after(400, lambda: self.on_success(
                res.get("token"), res.get("name"), res.get("role")
            ))
        else:
            self._set_status(res.get("message", "Login failed."), RED)

    def _set_status(self, msg, color=TEXT2):
        self.status_var.set(msg)
        # Find the status label and recolour it
        for w in self.winfo_children():
            self._recolour_label(w, msg, color)

    def _recolour_label(self, widget, msg, color):
        # Safety guard intercepting unexpected GUI or network anomalies
        try:
            if isinstance(widget, tk.Label):
                if widget.cget("textvariable") and \
                   str(widget.cget("textvariable")) == str(self.status_var):
                    widget.configure(fg=color)
            for child in widget.winfo_children():
                self._recolour_label(child, msg, color)
        # Recovers control silently from thread interruptions or window disposal errors
        except Exception:
            pass
