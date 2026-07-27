# ============================================================
#  EmpowerAccess Desktop — config.py
#  Central configuration for all modules
# ============================================================

import os

# ── App Identity ──────────────────────────────────────────
APP_NAME        = "EmpowerAccess"
APP_VERSION     = "1.0.0"
APP_SUBTITLE    = "Accessibility AI · v1.0"
APP_MOTTO       = "Never Stop Yourself"

# ── Flask Backend ─────────────────────────────────────────
FLASK_BASE_URL  = "http://localhost:5000"
API_TIMEOUT     = 35   # seconds

# ── JWT Storage ───────────────────────────────────────────
TOKEN_FILE      = os.path.join(os.path.expanduser("~"), ".empoweraccess_token")

# ── Whisper STT ───────────────────────────────────────────
WHISPER_MODEL   = "small"        # tiny / base / small / medium
SAMPLE_RATE     = 16000
RECORD_SECONDS  = 7             # max recording window

# ── TTS Configuration ──────────────────────────────────────
# Provider options: "edge" | "openai" | "elevenlabs" | "offline"
TTS_PROVIDER        = "edge"
USE_OFFLINE_TTS     = False    # Global override: True = pyttsx3

# Edge TTS (High Quality & Free)
EDGE_TTS_VOICE      = "en-US-ChristopherNeural"

# ── Gemini (already in your Flask backend) ───────────────
# The .exe calls /api/user/ai which proxies to Gemini.
# No key needed here — it's handled server-side.

# ── Window Geometry ───────────────────────────────────────
TOOLBAR_W       = 1300
TOOLBAR_H       = 49
MAIN_W          = 1300
MAIN_H          = 959

# ── Colours (matches EmpowerAccess web design system) ─────
DARK_THEME = {
    "bg":           "#000000",
    "bg2":          "#000000",
    "bg3":          "#000000",
    "bg4":          "#000000",
    "teal":         "#0E9E82",
    "teal2":        "#0bc49a",
    "gold":         "#E1C300",
    "text":         "#e2e8f0",
    "text2":        "#8b9ab0",
    "border":       "#2a3448",
    "green":        "#39d353",
    "red":          "#f85149",
    "blue":         "#4da6ff",
    "yellow":       "#f0c000",
}

LIGHT_THEME = {
    "bg":           "#f0ece4",
    "bg2":          "#ebe6dd",
    "bg3":          "#faf7f2",
    "bg4":          "#ffffff",
    "teal":         "#0E9E82",
    "teal2":        "#0bc49a",
    "gold":         "#E1C300",
    "text":         "#1e1b2e",
    "text2":        "#4a4560",
    "border":       "#333333",
    "green":        "#059669",
    "red":          "#dc2626",
    "blue":         "#2563eb",
    "yellow":       "#d97706",
}

THEME = DARK_THEME

