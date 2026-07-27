# ============================================================
#  EmpowerAccess Desktop — ui/theme.py
#  Centralised colours, fonts, and styled widget factory
# ============================================================

# Imports standard Tkinter toolkit to manage window elements
import tkinter as tk
from tkinter import ttk
import ctypes
from config import THEME


# ── Colour shortcuts ──────────────────────────────────────────────────────────
BG      = THEME["bg"]
BG2     = THEME["bg2"]
BG3     = THEME["bg3"]
BG4     = THEME["bg4"]
TEAL    = THEME["teal"]
TEAL2   = THEME["teal2"]
GOLD    = THEME["gold"]
TEXT    = THEME["text"]
TEXT2   = THEME["text2"]
BORDER  = THEME["border"]
GREEN   = THEME["green"]
RED     = THEME["red"]
BLUE    = THEME["blue"]

def update_theme_constants(new_theme):
    global BG, BG2, BG3, BG4, TEAL, TEAL2, GOLD, TEXT, TEXT2, BORDER, GREEN, RED, BLUE, YELLOW
    BG      = new_theme["bg"]
    BG2     = new_theme["bg2"]
    BG3     = new_theme["bg3"]
    BG4     = new_theme["bg4"]
    TEAL    = new_theme["teal"]
    TEAL2   = new_theme["teal2"]
    GOLD    = new_theme["gold"]
    TEXT    = new_theme["text"]
    TEXT2   = new_theme["text2"]
    BORDER  = new_theme["border"]
    GREEN   = new_theme["green"]
    RED     = new_theme["red"]
    BLUE    = new_theme["blue"]
    YELLOW  = new_theme.get("yellow", "#f0c000")

    # Critical: Propagate updated constants to all modules that imported them.
    # Without this, modules like main_panel.py will keep using their stale 'from theme import *' copies.
    import sys
    constants = {
        "BG": BG, "BG2": BG2, "BG3": BG3, "BG4": BG4,
        "TEAL": TEAL, "TEAL2": TEAL2, "GOLD": GOLD,
        "TEXT": TEXT, "TEXT2": TEXT2, "BORDER": BORDER,
        "GREEN": GREEN, "RED": RED, "BLUE": BLUE, "YELLOW": YELLOW
    }
    for mod_name, mod in list(sys.modules.items()):
        if mod and (mod_name.startswith("ui.") or mod_name == "gui_app" or mod_name == "__main__"):
            for k, v in constants.items():
                if hasattr(mod, k):
                    setattr(mod, k, v)


FONT        = ("Segoe UI", 11)
FONT_SM     = ("Segoe UI", 9)
FONT_MD     = ("Segoe UI", 12)
FONT_LG     = ("Segoe UI", 14, "bold")
FONT_XL     = ("Segoe UI", 18, "bold")
FONT_ITALIC = ("Segoe UI", 15, "bold italic")
FONT_MONO   = ("Courier New", 10)
FONT_BADGE  = ("Segoe UI", 9, "bold")
FONT_CAPS   = ("Segoe UI", 8, "bold")


# Sets parent font parameters, active margins, colors, and button widgets
def apply_global_style(root: tk.Tk):
    """Apply ttk styles for a consistent dark theme throughout the app."""
    style = ttk.Style(root)
    style.theme_use("clam")

    style.configure(".",
        background=BG2,
        foreground=TEXT,
        borderwidth=0,
        highlightthickness=0
    )
    style.configure("TFrame",  background=BG2)
    style.configure("TLabel",  background=BG2, foreground=TEXT,  font=FONT)
    style.configure("TButton", background=BG3, foreground=TEXT,  font=FONT,
                    borderwidth=1, relief="flat")
    style.map("TButton",
        background=[("active", BG4), ("pressed", TEAL)],
        foreground=[("active", TEXT)]
    )
    style.configure("TEntry",
        fieldbackground=BG3, foreground=TEXT, insertcolor=TEXT,
        borderwidth=1, relief="flat"
    )
    style.configure("Vertical.TScrollbar",
        background=BG3, troughcolor=BG2, arrowcolor=TEXT2,
        borderwidth=0
    )
    
    # Modern smooth scrollbar without arrows
    style.layout("Smooth.Vertical.TScrollbar",
        [('Vertical.Scrollbar.trough',
          {'children': [('Vertical.Scrollbar.thumb',
                         {'expand': '1', 'sticky': 'nswe'})],
           'sticky': 'ns'})]
    )
    style.configure("Smooth.Vertical.TScrollbar",
        background="#2a2a2a", troughcolor=BG, borderwidth=2, relief="flat",
        darkcolor=BG, lightcolor=BG, bordercolor=BG
    )
    style.map("Smooth.Vertical.TScrollbar",
        background=[("active", TEXT2), ("pressed", TEXT2)]
    )

    style.configure("TProgressbar",
        troughcolor=BORDER, background=GREEN, borderwidth=2, thickness=4
    )


# ── Reusable widget helpers ───────────────────────────────────────────────────

# Modular visual constructor layout widgets wrapping parent configurations
def frame(parent, bg=BG2, **kw) -> tk.Frame:
    # Bubbles computed parameters back to caller functions
    return tk.Frame(parent, bg=bg, **kw)


# Modular visual constructor layout widgets wrapping parent configurations
def label(parent, text="", bg=BG2, fg=TEXT, font=FONT, **kw) -> tk.Label:
    # Bubbles computed parameters back to caller functions
    return tk.Label(parent, text=text, bg=bg, fg=fg, font=font, **kw)


def button(parent, text="", command=None, bg=BG3, fg=TEXT,
           font=FONT, hover_bg=BG4, relief="flat", **kw) -> tk.Button:
    btn = tk.Button(parent, text=text, command=command, bg=bg, fg=fg,
                    font=font, relief=relief, bd=0,
                    activebackground=hover_bg, activeforeground=TEXT,
                    cursor="hand2", **kw)
    btn.bind("<Enter>", lambda e: btn.config(bg=hover_bg))
    btn.bind("<Leave>", lambda e: btn.config(bg=bg))
    # Bubbles computed parameters back to caller functions
    return btn


def teal_button(parent, text="", command=None, font=FONT, **kw) -> tk.Button:
    btn = tk.Button(parent, text=text, command=command,
                    bg=TEAL, fg="#ffffff",
                    font=font, relief="flat", bd=0,
                    activebackground=TEAL2, activeforeground="#ffffff",
                    cursor="hand2", **kw)
    btn.bind("<Enter>", lambda e: btn.config(bg=TEAL2))
    btn.bind("<Leave>", lambda e: btn.config(bg=TEAL))
    # Bubbles computed parameters back to caller functions
    return btn


def danger_button(parent, text="", command=None, font=FONT, **kw) -> tk.Button:
    btn = tk.Button(parent, text=text, command=command,
                    bg=BG3, fg=RED,
                    font=font, relief="flat", bd=0,
                    activebackground="#2a1a1a", activeforeground=RED,
                    cursor="hand2", **kw)
    # Bubbles computed parameters back to caller functions
    return btn


class RoundedButton(tk.Canvas):
    """
    Premium button with rounded corners, optional icon, outline ring,
    hover colour transition, and press-depth animation.

    Extra Parameters
    ----------------
    icon        : emoji / unicode char shown above the label (optional)
    icon_fg     : colour for the icon  (defaults to fg)
    outline_col : colour of the 1-px border ring (None = no border)
    """
    def __init__(self, parent, text="", command=None, radius=18,
                 bg=BG3, fg=TEXT, hover_bg=BG4,
                 width=130, height=48, font=FONT_SM,
                 icon="", icon_fg=None, outline_col=None, **kw):
        super().__init__(parent, bg=parent["bg"], bd=0, highlightthickness=0,
                         width=width, height=height, cursor="hand2", **kw)
        self._label     = text
        self._cmd       = command
        self._radius    = radius
        self._normal_bg = bg
        self._hover_bg  = hover_bg
        if self._normal_bg == self._hover_bg:
            # Safety guard intercepting unexpected GUI or network anomalies
            try:
                h = self._normal_bg.lstrip("#")
                if len(h) == 6:
                    r, g, b = int(h[0:2],16), int(h[2:4],16), int(h[4:6],16)
                    self._hover_bg = f"#{min(255,r+25):02x}{min(255,g+25):02x}{min(255,b+25):02x}"
                else:
                    self._hover_bg = "#1a1a1a"
            # Recovers control silently from thread interruptions or window disposal errors
            except Exception:
                self._hover_bg = "#1a1a1a"
        self._fg        = fg
        self._icon_fg   = icon_fg or fg
        self._font      = font
        self._icon      = icon
        self._outline   = outline_col
        self._bw        = width    # NOTE: _w is reserved by tkinter; use _bw/_bh
        self._bh        = height
        self._pressed   = False

        self._draw(bg)

        self.bind("<Enter>",           self._on_enter)
        self.bind("<Leave>",           self._on_leave)
        self.bind("<ButtonPress-1>",   self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)

    # ── Drawing ──────────────────────────────────────────────────────────────

    def _rounded_polygon(self, x, y, w, h, r, **kw):
        pts = [x+r,y, x+r,y, x+w-r,y, x+w-r,y,
               x+w,y, x+w,y+r, x+w,y+r, x+w,y+h-r,
               x+w,y+h-r, x+w,y+h, x+w-r,y+h, x+w-r,y+h,
               x+r,y+h, x+r,y+h, x,y+h, x,y+h-r,
               x,y+h-r, x,y+r, x,y+r, x,y]
        # Bubbles computed parameters back to caller functions
        return self.create_polygon(pts, smooth=True, **kw)

    @staticmethod
    def _darken(hex_col: str, amt: int) -> str:
        # Safety guard intercepting unexpected GUI or network anomalies
        try:
            h = hex_col.lstrip("#")
            if len(h) != 6:
                # Bubbles computed parameters back to caller functions
                return hex_col
            r, g, b = int(h[0:2],16), int(h[2:4],16), int(h[4:6],16)
            # Bubbles computed parameters back to caller functions
            return f"#{max(0,r-amt):02x}{max(0,g-amt):02x}{max(0,b-amt):02x}"
        # Recovers control silently from thread interruptions or window disposal errors
        except Exception:
            # Bubbles computed parameters back to caller functions
            return hex_col

    @staticmethod
    def _interpolate_color(c1: str, c2: str, factor: float) -> str:
        # Safety guard intercepting unexpected GUI or network anomalies
        try:
            h1 = c1.lstrip("#")
            h2 = c2.lstrip("#")
            if len(h1) != 6 or len(h2) != 6: return c2 if factor > 0.5 else c1
            r1, g1, b1 = int(h1[0:2],16), int(h1[2:4],16), int(h1[4:6],16)
            r2, g2, b2 = int(h2[0:2],16), int(h2[2:4],16), int(h2[4:6],16)
            r = int(r1 + (r2 - r1) * factor)
            g = int(g1 + (g2 - g1) * factor)
            b = int(b1 + (b2 - b1) * factor)
            # Bubbles computed parameters back to caller functions
            return f"#{r:02x}{g:02x}{b:02x}"
        # Recovers control silently from thread interruptions or window disposal errors
        except Exception:
            # Bubbles computed parameters back to caller functions
            return c2 if factor > 0.5 else c1

    def _draw(self, bg_col):
        # Safety guard intercepting unexpected GUI or network anomalies
        try:
            self.delete("all")
            w, h, r = self._bw, self._bh, self._radius
            dy = 1 if self._pressed else 0          # press displacement

            # Shadow
            self._rounded_polygon(2, 3, w-4, h-4, r,
                                   fill=self._darken(bg_col, 30), outline="")
            # Body
            self._rounded_polygon(0, dy, w-2, h-4, r, fill=bg_col, outline="")
            # Outline ring
            if self._outline:
                self._rounded_polygon(0, dy, w-2, h-4, r,
                                      fill="", outline=self._outline, width=1)

            # Text layout — use standard Segoe UI (no emoji font) to avoid TclError
            cx = w // 2
            icon_font  = ("Segoe UI", 13, "bold")
            icon_font2 = ("Segoe UI", 11, "bold")
            if self._icon and self._label:
                self.create_text(cx, h//2 - 9 + dy, text=self._icon,
                                 fill=self._icon_fg, font=icon_font2)
                self.create_text(cx, h//2 + 9 + dy, text=self._label,
                                 fill=self._fg, font=self._font)
            elif self._icon:
                self.create_text(cx, h//2 + dy, text=self._icon,
                                 fill=self._icon_fg, font=icon_font)
            else:
                self.create_text(cx, h//2 + dy, text=self._label,
                                 fill=self._fg, font=self._font)
        # Recovers control silently from thread interruptions or window disposal errors
        except Exception:
            # Last-resort fallback: plain flat button so the UI is never broken
            # Safety guard intercepting unexpected GUI or network anomalies
            try:
                self.delete("all")
                self.create_rectangle(0, 0, self._bw, self._bh,
                                      fill=bg_col, outline="")
                self.create_text(self._bw//2, self._bh//2,
                                 text=self._label, fill=self._fg,
                                 font=self._font)
            # Recovers control silently from thread interruptions or window disposal errors
            except Exception:
                pass

    # ── Events ───────────────────────────────────────────────────────────────

    def _on_enter(self, _):
        self._hovering = True
        self._animate_hover()

    def _on_leave(self, _):
        self._hovering = False
        self._pressed = False
        self._animate_hover()

    def _on_press(self, _):
        self._pressed = True
        self._draw(self._hover_bg)

    def _on_release(self, _):
        self._pressed = False
        self._draw(self._hover_bg)
        if self._cmd:
            self._cmd()

    def _animate_hover(self):
        if hasattr(self, "_hover_job") and self._hover_job:
            self.after_cancel(self._hover_job)
            self._hover_job = None
            
        if not hasattr(self, "_hover_factor"):
            self._hover_factor = 0.0
            
        target = 1.0 if getattr(self, "_hovering", False) else 0.0
        
        if abs(self._hover_factor - target) < 0.05:
            self._hover_factor = target
            current_bg = self._interpolate_color(self._normal_bg, self._hover_bg, self._hover_factor)
            self._draw(current_bg)
            # Bubbles computed parameters back to caller functions
            return
            
        self._hover_factor += (target - self._hover_factor) * 0.3
        current_bg = self._interpolate_color(self._normal_bg, self._hover_bg, self._hover_factor)
        self._draw(current_bg)
        self._hover_job = self.after(20, self._animate_hover)



class RoundedFrame(tk.Canvas):
    """Decorative container with rounded corners, consistent background, and optional border."""
    def __init__(self, parent, radius=20, bg=BG2, outline="", border_width=1, **kw):
        super().__init__(parent, bg=parent["bg"], bd=0, highlightthickness=0, **kw)
        self.radius = radius
        self.bg = bg
        self.outline = outline
        self.border_width = border_width
        self.bind("<Configure>", lambda e: self._draw())

    def _draw(self, *args, **kwargs):
        """Redraw the rounded rectangle. Accepts args for theme-update compatibility."""
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        r = self.radius
        self._draw_rounded_rect(0, 0, w, h, r, fill=self.bg, outline=self.outline, width=self.border_width)

    def _draw_rounded_rect(self, x, y, w, h, r, **kw):
        # Slightly inset the coordinates if there's a border to prevent clipping
        if self.outline:
            x, y, w, h = x+1, y+1, w-2, h-2
        points = [x+r, y, x+r, y, x+w-r, y, x+w-r, y, x+w, y, x+w, y+r, x+w, y+r, x+w, y+h-r, x+w, y+h-r, x+w, y+h, x+w-r, y+h, x+w-r, y+h, x+r, y+h, x+r, y+h, x, y+h, x, y+h-r, x, y+h-r, x, y+r, x, y+r, x, y]
        # Bubbles computed parameters back to caller functions
        return self.create_polygon(points, smooth=True, **kw)


# Modular visual constructor layout widgets wrapping parent configurations
def entry(parent, textvariable=None, show=None, font=FONT, **kw) -> tk.Entry:
    e = tk.Entry(parent, textvariable=textvariable, show=show,
                 bg=BG3, fg=TEXT, insertbackground=TEXT,
                 relief="flat", bd=0, font=font,
                 highlightthickness=1, highlightcolor=TEAL,
                 highlightbackground=BORDER, **kw)
    # Bubbles computed parameters back to caller functions
    return e


def separator(parent, orient="h", bg=BORDER) -> tk.Frame:
    if orient == "h":
        # Bubbles computed parameters back to caller functions
        return tk.Frame(parent, bg=bg, height=1)
    # Bubbles computed parameters back to caller functions
    return tk.Frame(parent, bg=bg, width=1)


def card(parent, bg=BG3, padx=12, pady=10, radius=12, **kw) -> tk.Frame:
    """A bordered card container with rounded corners."""
    outer = RoundedFrame(parent, radius=radius, bg=BORDER, **kw)
    inner = tk.Frame(outer, bg=bg)
    inner.pack(fill="both", expand=True, padx=1, pady=1, ipadx=padx, ipady=pady)
    # Bubbles computed parameters back to caller functions
    return outer, inner


def scrolled_text(parent, bg=BG3, fg=TEXT, font=FONT_MONO,
                  state="disabled", **kw) -> tk.Text:
    from tkinter import scrolledtext
    st = scrolledtext.ScrolledText(
        parent, bg=bg, fg=fg, font=font,
        relief="flat", bd=0,
        insertbackground=TEXT,
        selectbackground=TEAL, selectforeground="#fff",
        state=state, wrap="word",
        highlightthickness=0, **kw
    )
    st.vbar.configure(
        bg=BG3, troughcolor=BG2, activebackground=BORDER,
        highlightthickness=0, relief="flat", bd=0
    )
    # Bubbles computed parameters back to caller functions
    return st


def append_chat(widget: tk.Text, text: str, tag: str):
    """Append a line to a chat Text widget with colour tagging."""
    widget.configure(state="normal")
    widget.insert("end", text + "\n", tag)
    widget.see("end")
    widget.configure(state="disabled")


# Binds visual Win32 border handlers to curve top-level window edges
def set_rounded_corners(window: tk.Toplevel | tk.Tk):
    """Use Windows DWM API to set rounded corners for a borderless window."""
    # Safety guard intercepting unexpected GUI or network anomalies
    try:
        # Get the window handle (HWND)
        hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
        
        # DWMWA_WINDOW_CORNER_PREFERENCE = 33
        # DWMWCP_ROUND = 2 (Standard rounded)
        # DWMWCP_ROUNDSMALL = 3 (Slightly rounded)
        DWMWA_WINDOW_CORNER_PREFERENCE = 33
        preference = ctypes.c_int(2)
        
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd,
            DWMWA_WINDOW_CORNER_PREFERENCE,
            ctypes.byref(preference),
            ctypes.sizeof(preference)
        )
    # Recovers control silently from thread interruptions or window disposal errors
    except Exception as e:
        print(f"[Theme] Failed to set rounded corners: {e}")

def update_all_widgets_theme(root, theme):
    """Recursively updates the theme of all widgets in the application."""
    # Capture old values before updating to new ones
    old_bg      = BG
    old_bg2     = BG2
    old_bg3     = BG3
    old_bg4     = BG4
    old_border  = BORDER
    old_text    = TEXT
    old_text2   = TEXT2
    old_teal    = TEAL
    old_green   = GREEN
    old_red     = RED
    old_blue    = BLUE
    old_gold    = GOLD

    update_theme_constants(theme)
    apply_global_style(root)
    
    is_dark = (BG == "#000000")

    def _update_recursive(widget):
        w_type = widget.winfo_class()
        
        # Safety guard intercepting unexpected GUI or network anomalies
        try:
            # Get current background to check if it matches a theme constant
            curr_bg = widget.cget("bg")
            
            if w_type in ("Frame", "Labelframe", "TFrame"):
                # Intelligent update: only change if it was using a standard theme color
                if curr_bg == old_border:   widget.configure(bg=BORDER)
                elif curr_bg == old_bg3:    widget.configure(bg=BG3)
                elif curr_bg == old_bg4:    widget.configure(bg=BG4)
                elif curr_bg == old_bg:     widget.configure(bg=BG)
                elif curr_bg == old_green:  widget.configure(bg=GREEN)
                elif curr_bg == old_red:    widget.configure(bg=RED)
                elif curr_bg == old_blue:   widget.configure(bg=BLUE)
                elif curr_bg == old_gold:   widget.configure(bg=GOLD)
                elif curr_bg == old_teal:   widget.configure(bg=TEAL)
                else:
                    # Default for most frames
                    widget.configure(bg=BG2)

            elif w_type == "Label" or w_type == "TLabel":
                curr_fg = widget.cget("fg")
                new_fg = TEXT
                if curr_fg == old_text2:    new_fg = TEXT2
                elif curr_fg == old_green:  new_fg = GREEN
                elif curr_fg == old_red:    new_fg = RED
                elif curr_fg == old_blue:   new_fg = BLUE
                elif curr_fg == old_gold:   new_fg = GOLD
                elif curr_fg == old_teal:   new_fg = TEAL
                elif curr_fg == TEAL2:      new_fg = TEAL2 # Keep teal2
                
                widget.configure(bg=widget.master["bg"], fg=new_fg)

            elif w_type == "Button" or w_type == "TButton":
                widget.configure(bg=BG3, fg=TEXT)

            elif w_type == "Canvas":
                if hasattr(widget, "_draw"): 
                    # Custom widgets (RoundedButton, RoundedFrame)
                    widget.configure(bg=widget.master["bg"])
                    
                    if hasattr(widget, "_normal_bg"):
                        # It's a RoundedButton
                        if hasattr(widget, "_is_sos_btn"):
                            widget._normal_bg = "#3a0a0a" if is_dark else "#fff5f5"
                            widget._hover_bg  = "#5c1010" if is_dark else "#ffe3e3"
                            widget._fg        = "#ff8080" if is_dark else "#c92a2a"
                        elif hasattr(widget, "_is_weather_btn"):
                            widget._normal_bg = "#0a1f1f" if is_dark else "#f0fdfa"
                            widget._hover_bg  = "#0d2e2e" if is_dark else "#ccfbf1"
                            widget._fg        = TEAL2     if is_dark else "#0d9488"
                        elif widget._normal_bg == old_bg3:
                            widget._normal_bg = BG3
                            widget._hover_bg = BG4
                            widget._fg = TEXT
                        # If it has custom colors (like SOS button), we might want to skip or handle specially
                    
                    if hasattr(widget, "bg") and hasattr(widget, "outline"):
                        # It's a RoundedFrame
                        if widget.bg == old_bg3:      widget.bg = BG3
                        elif widget.bg == old_bg2:    widget.bg = BG2
                        
                        if widget.outline == old_border: widget.outline = BORDER
                        
                        # Specialized handling for chat bubbles (stored on widget in main_panel.py)
                        if hasattr(widget, "_is_user_bubble"):
                            if is_dark:
                                widget.bg = "#151515" if widget._is_user_bubble else "#0a0a0a"
                                widget.outline = GREEN if widget._is_user_bubble else "#ffffff"
                            else:
                                widget.bg = BG4 if widget._is_user_bubble else BG3
                                widget.outline = TEAL if widget._is_user_bubble else BORDER

                    widget._draw(BG3) # Pass a color just in case it's a button
                else:
                    widget.configure(bg=BG2)

            elif w_type == "Text" or w_type == "ScrolledText":
                widget.configure(bg=BG4, fg=TEXT, insertbackground=TEXT)
                # Safety guard intercepting unexpected GUI or network anomalies
                try:
                    u_bg = "#0c0c0c" if is_dark else BG4
                    b_bg = "#050505" if is_dark else BG3
                    t_fg = "white"   if is_dark else TEXT2

                    widget.tag_configure("user",     foreground=TEXT)
                    widget.tag_configure("bot",      foreground=TEAL2)
                    widget.tag_configure("user_msg", background=u_bg)
                    widget.tag_configure("bot_msg",  background=b_bg)
                    widget.tag_configure("time",     foreground=t_fg)
                    widget.tag_configure("sys",      foreground=GOLD)
                    widget.tag_configure("error",    foreground=RED)
                except:
                    pass
            elif w_type == "Entry" or w_type == "TEntry":
                widget.configure(bg=BG4, fg=TEXT, insertbackground=TEXT)
        except:
            pass

        for child in widget.winfo_children():
            _update_recursive(child)

    _update_recursive(root)

