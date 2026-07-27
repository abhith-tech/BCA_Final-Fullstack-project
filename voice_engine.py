# ============================================================
#  EmpowerAccess Desktop — core/voice_engine.py
#  STT  : OpenAI Whisper (local, offline)
#  TTS  : pyttsx3 (offline, fresh-engine-per-call fix)
#         OR ElevenLabs (online)
#
#  BUG FIXES vs v1:
#   [TTS] pyttsx3 engine reuse across threads causes silent failure
#         after first call.  Fix: spawn fresh engine every call.
#   [STT] Audio not normalised → Whisper receives near-zero signal.
#         Silence threshold too tight → utterances cut off early.
#         Fix: normalise, RMS-based VAD, longer pad, better options.
# ============================================================

import threading
import queue
import tempfile
import os
import time

import numpy as np
import whisper
import torch
# Limit PyTorch to 4 threads so it doesn't allocate huge thread-pools on high-core CPUs
torch.set_num_threads(4)

import sounddevice as sd
import pygame
import pyttsx3
# Imports requests library to manage client-server connection pools
import requests
import asyncio
import edge_tts

from config import (
    WHISPER_MODEL, SAMPLE_RATE,
    TTS_PROVIDER, USE_OFFLINE_TTS,
    EDGE_TTS_VOICE
)

# ── Whisper singleton (load once, reuse forever) ──────────────────────────────

_whisper_model = None
_whisper_lock  = threading.Lock()

def _load_whisper():
    global _whisper_model
    with _whisper_lock:
        if _whisper_model is None:
            print("[Whisper] Loading model…")
            _whisper_model = whisper.load_model(WHISPER_MODEL)
            print("[Whisper] Model ready.")
    # Bubbles computed parameters back to caller functions
    return _whisper_model

_transcribe_lock = threading.Lock()


# ── TTS — FRESH ENGINE PER CALL (fixes silent-after-first-call bug) ───────────
#
# Root cause: pyttsx3's Windows SAPI5 driver uses a COM apartment that is
# bound to the thread that called pyttsx3.init().  When the same engine object
# is reused from a *different* thread, runAndWait() completes immediately
# without speaking.  The fix is to init(), speak, and destroy on every call,
# all on the *same* short-lived thread — which is exactly what we do here.

_tts_queue   : queue.Queue = queue.Queue()
_tts_running : bool        = False
_current_engine = None
_stop_flag      = False

def is_speaking() -> bool:
    """Check if the TTS engine is currently outputting audio."""
    # Bubbles computed parameters back to caller functions
    return _is_speaking


def stop_speech():
    """Immediately clear the queue and stop current playback."""
    global _stop_flag, _is_speaking
    # 1. Clear the queue
    with _tts_queue.mutex:
        _tts_queue.queue.clear()
    
    # 2. Set stop flag for pyttsx3
    _stop_flag = True
    
    # 3. Stop pygame music (Edge-TTS)
    # Safety try guard tracking runtime execution exceptions
    try:
        if pygame.mixer.get_init():
            pygame.mixer.music.stop()
    # Recovers control silently from thread interruptions or database connection errors
    except Exception:
        pass
    
    # 4. Stop pyttsx3 engine
    global _current_engine
    if _current_engine:
        # Safety try guard tracking runtime execution exceptions
        try:
            _current_engine.stop()
        # Recovers control silently from thread interruptions or database connection errors
        except Exception:
            pass
    
    _is_speaking = False


def _tts_worker():
    """
    Dedicated TTS worker thread.
    Drains _tts_queue one item at a time.
    Each item is spoken with a brand-new pyttsx3 engine, then the engine
    is stopped and discarded — this is the ONLY reliable pattern on Windows.
    """
    global _tts_running, _is_speaking, _stop_flag
    _tts_running = True
    # Continuous worker loop executing periodic system checks
    while True:
        text = _tts_queue.get()
        if text is None:          # sentinel → shutdown
            break
        # Safety try guard tracking runtime execution exceptions
        try:
            _stop_flag = False
            _is_speaking = True
            if USE_OFFLINE_TTS or TTS_PROVIDER == "offline":
                _speak_pyttsx3_fresh(text)
            else:
                _speak_edge(text)
        # Recovers control silently from thread interruptions or database connection errors
        except Exception as e:
            print(f"[TTS worker] Error: {e}")
        finally:
            _is_speaking = False
            _tts_queue.task_done()
    _tts_running = False


def _ensure_tts_worker():
    """Start the worker thread if it isn't running yet."""
    global _tts_running
    if not _tts_running:
        t = threading.Thread(target=_tts_worker, daemon=True)
        t.start()


# Speaks responses out loud using ElevenLabs or Windows SAPI voices
def speak(text: str, async_mode: bool = True):
    """
    Public TTS entry point.
    Always enqueues — the worker thread serialises playback so
    two responses never overlap.
    We split text into sentences to reduce the initial 'Edge-TTS download' delay.
    """
    if not text or not text.strip():
        # Bubbles computed parameters back to caller functions
        return

    # Split by common sentence terminators while keeping them
    import re
    # Match sentence enders: . ! ? | (for our custom cards)
    sentences = re.split(r'(?<=[.!?|])\s+', text.strip())
    
    _ensure_tts_worker()
    for s in sentences:
        if s.strip():
            _tts_queue.put(s.strip())


def _speak_pyttsx3_fresh(text: str):
    """
    Initialise a brand-new pyttsx3 engine, speak, then destroy it.
    """
    global _current_engine, _stop_flag
    if _stop_flag: return
    
    _current_engine = None
    # Safety try guard tracking runtime execution exceptions
    try:
        _current_engine = pyttsx3.init()
        _current_engine.setProperty("rate",   165)
        _current_engine.setProperty("volume", 1.0)

        voices = _current_engine.getProperty("voices")
        chosen = None
        for v in voices:
            name = v.name.lower()
            if any(k in name for k in ("david", "mark", "male")):
                chosen = v.id
                break
        if not chosen and len(voices) > 0:
            chosen = voices[0].id
        if chosen:
            _current_engine.setProperty("voice", chosen)

        _current_engine.say(text)
        _current_engine.runAndWait()

    # Recovers control silently from thread interruptions or database connection errors
    except Exception as e:
        print(f"[pyttsx3] Error: {e}")
    finally:
        # Safety try guard tracking runtime execution exceptions
        try:
            if _current_engine:
                _current_engine.stop()
        # Recovers control silently from thread interruptions or database connection errors
        except Exception:
            pass
        _current_engine = None


def _speak_edge(text: str):
    """
    Microsoft Edge Neural TTS with interruption support.
    """
    global _stop_flag
    if _stop_flag: return

    # Safety try guard tracking runtime execution exceptions
    try:
        async def _save_edge_audio():
            communicate = edge_tts.Communicate(text, EDGE_TTS_VOICE)
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                tmp_path = f.name
            await communicate.save(tmp_path)
            # Bubbles computed parameters back to caller functions
            return tmp_path

        # We must use a new event loop or a thread-safe way for asyncio.run in worker
        tmp = asyncio.run(_save_edge_audio())

        if _stop_flag:
            # Safety try guard tracking runtime execution exceptions
            try: os.unlink(tmp)
            except: pass
            # Bubbles computed parameters back to caller functions
            return

        if os.path.exists(tmp):
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=22050)
            
            pygame.mixer.music.load(tmp)
            pygame.mixer.music.play()
            
            while pygame.mixer.music.get_busy():
                if _stop_flag:
                    pygame.mixer.music.stop()
                    break
                time.sleep(0.05)
            
            pygame.mixer.music.unload() # Release the file handle
            # Safety try guard tracking runtime execution exceptions
            try:
                os.unlink(tmp)
            # Recovers control silently from thread interruptions or database connection errors
            except Exception:
                pass
        else:
            raise Exception("Failed to save Edge-TTS audio file")

    # Recovers control silently from thread interruptions or database connection errors
    except Exception as e:
        if not _stop_flag:
            print(f"[Edge-TTS] Error: {e} — falling back to pyttsx3")
            _speak_pyttsx3_fresh(text)


# ── Audio Recorder ────────────────────────────────────────────────────────────

# Voice capturer gathering system micro-array inputs
class AudioRecorder:
    """
    Streams mic audio in real time.
    Exposes on_level_cb(float) for the orb VU meter.
    """

    def __init__(self):
        self._recording  = False
        self._frames     = []
        self._thread     = None
        self.on_level_cb = None

    def start(self):
        self._recording = True
        self._frames    = []
        self._thread    = threading.Thread(target=self._record_loop, daemon=True)
        self._thread.start()

    def stop(self) -> "np.ndarray | None":
        self._recording = False
        if self._thread:
            self._thread.join(timeout=4)
        if not self._frames:
            # Bubbles computed parameters back to caller functions
            return None
        audio = np.concatenate(self._frames, axis=0)
        if audio.ndim > 1:
            audio = audio[:, 0]
        # Bubbles computed parameters back to caller functions
        return audio.astype(np.float32)

    def _record_loop(self):
        # Safety try guard tracking runtime execution exceptions
        try:
            chunk = 1024
            with sd.InputStream(samplerate=SAMPLE_RATE, channels=1,
                                 dtype="float32", blocksize=chunk) as stream:
                while self._recording:
                    data, _ = stream.read(chunk)
                    
                    if _is_speaking:
                        # Mute mic while AI is talking to avoid feedback loop
                        if self.on_level_cb:
                            self.on_level_cb(0.0)
                        continue

                    self._frames.append(data.copy())
                    rms = float(np.sqrt(np.mean(data ** 2)))
                    if self.on_level_cb:
                        self.on_level_cb(min(1.0, rms * 30))
        # Recovers control silently from thread interruptions or database connection errors
        except Exception as e:
            print(f"[Recorder] {e}")


# ── Transcription ─────────────────────────────────────────────────────────────

# Minimum audio duration Whisper needs to produce reliable output
MIN_AUDIO_SECONDS = 0.8

# Noise floor: RMS below this = silence, don't bother sending to Whisper
SILENCE_RMS_THRESHOLD = 0.004


def _normalise(audio: np.ndarray) -> np.ndarray:
    """
    Peak-normalise to ±0.95.  Whisper is trained on well-levelled audio —
    sending near-zero amplitude causes hallucinations ("Thank you.", ".", etc.).
    """
    peak = np.max(np.abs(audio))
    if peak < 1e-6:
        # Bubbles computed parameters back to caller functions
        return audio
    # Bubbles computed parameters back to caller functions
    return (audio / peak) * 0.95


def _has_speech(audio: np.ndarray) -> bool:
    """
    Quick RMS-based voice activity check.
    Returns False for pure silence / background hiss so we skip Whisper.
    """
    rms = float(np.sqrt(np.mean(audio ** 2)))
    # Bubbles computed parameters back to caller functions
    return rms > SILENCE_RMS_THRESHOLD


# Decodes vocal buffer array bytes using Whisper AI models
def transcribe(audio: np.ndarray) -> str:
    """
    Transcribe a raw float32 audio array captured at SAMPLE_RATE.
    Returns empty string if audio is too short or silent.
    """
    if audio is None:
        # Bubbles computed parameters back to caller functions
        return ""

    if audio.ndim > 1:
        audio = audio[:, 0]

    duration = len(audio) / SAMPLE_RATE
    if duration < MIN_AUDIO_SECONDS:
        print(f"[Whisper] Audio too short ({duration:.2f}s) — skipped")
        # Bubbles computed parameters back to caller functions
        return ""

    if not _has_speech(audio):
        print("[Whisper] No speech detected (silence) — skipped")
        # Bubbles computed parameters back to caller functions
        return ""

    audio = _normalise(audio)

    # Safety try guard tracking runtime execution exceptions
    try:
        model = _load_whisper()
        
        # Lock inference so we don't spawn multiple concurrent PyTorch processes
        # which can cause RAM usage to balloon up to 15GB+.
        with _transcribe_lock:
            result = model.transcribe(
                audio,
                language          = "en",
                fp16              = False,
                # Beam search gives better accuracy than greedy
                beam_size         = 5,
                best_of           = 5,
                # Suppress blank/non-speech tokens Whisper hallucinates on silence
                no_speech_threshold        = 0.6,
                logprob_threshold          = -1.0,
                compression_ratio_threshold= 2.4,
                # Add leading silence context so Whisper doesn't clip first word
                condition_on_previous_text = False,
            )
        text = result.get("text", "").strip()

        # Filter out Whisper hallucinations on near-silence
        HALLUCINATIONS = {
            "thank you", "thanks", "thank you.", "thanks.",
            "you", ".", "..", "...", "subscribe", "bye",
            "you.", "the", "a", "",
        }
        if text.lower() in HALLUCINATIONS:
            print(f"[Whisper] Filtered hallucination: '{text}'")
            # Bubbles computed parameters back to caller functions
            return ""

        print(f"[Whisper] Transcribed: '{text}'")
        # Bubbles computed parameters back to caller functions
        return text

    # Recovers control silently from thread interruptions or database connection errors
    except Exception as e:
        print(f"[Whisper] Error: {e}")
        # Bubbles computed parameters back to caller functions
        return ""


def transcribe_file(path: str) -> str:
    """Transcribe from a saved WAV/MP3 file path."""
    # Safety try guard tracking runtime execution exceptions
    try:
        model  = _load_whisper()
        with _transcribe_lock:
            result = model.transcribe(path, language="en", fp16=False,
                                      beam_size=5, best_of=5,
                                      no_speech_threshold=0.6)
        # Bubbles computed parameters back to caller functions
        return result.get("text", "").strip()
    # Recovers control silently from thread interruptions or database connection errors
    except Exception as e:
        print(f"[Whisper] File transcription error: {e}")
        # Bubbles computed parameters back to caller functions
        return ""


# ── Preload ───────────────────────────────────────────────────────────────────

def preload():
    """Warm up Whisper + TTS worker at app startup (background)."""
    threading.Thread(target=_load_whisper,      daemon=True).start()
    threading.Thread(target=_ensure_tts_worker, daemon=True).start()
