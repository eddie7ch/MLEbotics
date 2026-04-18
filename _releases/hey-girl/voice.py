"""
Voice I/O module — Gemini Live-style
- VAD-based recording (starts/stops automatically on speech)
- OpenAI Whisper API for high-quality speech-to-text
- OpenAI gpt-4o-mini-tts for natural, human-sounding voice output
- Barge-in: user can interrupt while AI is speaking
"""

import io
import os
import time
import wave
import threading
import tempfile
import numpy as np
import sounddevice as sd
import speech_recognition as sr
try:
    import cost_tracker as _cost
except ImportError:
    _cost = None

# ── Settings (runtime-editable) ───────────────────────────────────────────────
settings = {
    "engine": "openai",
    "openai_voice": "nova",
    "voice_instructions": "You are a real young woman having a relaxed, natural conversation. Speak with warm, genuine emotion — let your personality come through. Use natural human pacing with subtle pauses, slight breaths between phrases, and conversational rhythm. Vary your tone and energy like a real person would. Never sound flat, robotic, or read-aloud. Just talk like you're chatting with a friend.",
    "windows_voice_id": None,
    "rate": 175,
    "samplerate": 16000,
    "vad_threshold": 0.02,
    "silence_duration": 1.2,
    "max_record_seconds": 20,
    "microphone_device": None,   # None = system default; set to int device index to override
}


def get_input_devices() -> list[tuple[int, str]]:
    """Return list of (device_index, name) for all input devices."""
    devices = sd.query_devices()
    result = []
    for i, d in enumerate(devices):
        if d["max_input_channels"] > 0:
            result.append((i, d["name"]))
    return result

# ── Voice presets ──────────────────────────────────────────────────
VOICE_PRESETS = {
    "🇺🇸 Sweet American": {
        "voice": "nova",
        "instructions": "You are a warm, sweet young American woman chatting naturally. Speak with genuine emotion and human-like pacing — natural pauses, subtle breath between phrases, expressive tone. You are NOT a robot or text-to-speech system. Just talk like a real person, casually and warmly, with a soft American accent.",
    },
}

OPENAI_VOICES = {
    "Nova (US Female)": "nova",
}

# ── Barge-in state ────────────────────────────────────────────────────────────
_speaking = False
_barge_in_event = threading.Event()

# ── Error reporting callback (UI log) ────────────────────────────────────────
_error_cb = None          # callable(msg: str) or None
_quota_error_logged = False  # prevent repeated quota-exceeded spam
_use_fallback_tts = False    # switch to Windows TTS when OpenAI quota exceeded

def _speak_fallback(text: str):
    """Windows built-in TTS via pyttsx3 — free, offline, no API key needed."""
    global _speaking
    try:
        import pyttsx3
        engine = pyttsx3.init()
        engine.setProperty("rate", 175)
        voices = engine.getProperty("voices")
        # prefer a female voice if available
        for v in voices:
            if "female" in v.name.lower() or "zira" in v.name.lower() or "eva" in v.name.lower():
                engine.setProperty("voice", v.id)
                break
        _speaking = True
        engine.say(text)
        engine.runAndWait()
        _speaking = False
    except Exception:
        _speaking = False

def set_error_callback(fn):
    """Register a callback invoked with an error string when TTS fails."""
    global _error_cb
    _error_cb = fn

def _report_error(msg: str):
    if _error_cb:
        try:
            _error_cb(msg)
        except Exception:
            pass

# ── Recording-state callback (UI indicator) ───────────────────────────────────
_recording_state_cb = None  # callable(is_recording: bool) or None

def set_recording_state_callback(fn):
    """Register a callback invoked with True when VAD starts capturing, False when done."""
    global _recording_state_cb
    _recording_state_cb = fn

# ── Continuous RMS level callback (VU meter) ──────────────────────────────────
_level_cb = None          # callable(rms: float) or None
_vad_active   = False     # True while listen_vad() owns the mic
_monitor_active = False
_monitor_thread = None

def set_level_callback(fn):
    """Register a callback called ~20× per second with the current mic RMS (0.0–1.0)."""
    global _level_cb
    _level_cb = fn

def start_level_monitor():
    """Start a background thread that streams mic RMS when listen_vad is idle."""
    global _monitor_active, _monitor_thread
    _monitor_active = True
    if _monitor_thread and _monitor_thread.is_alive():
        return
    _monitor_thread = threading.Thread(target=_level_monitor_loop, daemon=True)
    _monitor_thread.start()

def stop_level_monitor():
    """Stop the background level monitor and zero the meter."""
    global _monitor_active
    _monitor_active = False
    if _level_cb:
        try:
            _level_cb(0.0)
        except Exception:
            pass

def _level_monitor_loop():
    """Background loop: reads small mic chunks and fires _level_cb."""
    sr_val = settings["samplerate"]
    chunk_size = int(sr_val * 0.05)   # 50 ms — responsive but light
    while _monitor_active:
        if _vad_active:              # listen_vad is running — it feeds the callback itself
            time.sleep(0.05)
            continue
        device = settings["microphone_device"]
        try:
            with sd.InputStream(samplerate=sr_val, channels=1, dtype="int16",
                                blocksize=chunk_size, device=device) as stream:
                while _monitor_active and not _vad_active:
                    chunk, _ = stream.read(chunk_size)
                    if _level_cb:
                        try:
                            _level_cb(_rms(chunk))
                        except Exception:
                            pass
        except Exception:
            time.sleep(0.5)


# ── OpenAI TTS (gpt-4o-mini-tts) with barge-in ───────────────────────────────

def _speak_openai(text: str):
    global _speaking
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key or api_key == "your_openai_key_here":
        # No API key — skip speech entirely (no robotic fallback)
        return
    try:
        import pygame
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        _barge_in_event.clear()

        instructions = settings.get("voice_instructions", "")
        kwargs = dict(
            model="gpt-4o-mini-tts",
            voice=settings.get("openai_voice", "nova"),
            input=text,
            response_format="mp3",
        )
        if instructions:
            kwargs["instructions"] = instructions

        response = client.audio.speech.create(**kwargs)
        audio_bytes = response.content

        if _cost:
            _cost.log_tts(text)

        pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
        sound = pygame.mixer.Sound(io.BytesIO(audio_bytes))

        _speaking = True
        channel = sound.play()

        while channel.get_busy():
            if _barge_in_event.is_set():
                channel.stop()
                break
            time.sleep(0.05)

        _speaking = False

    except Exception as e:
        _speaking = False
        global _quota_error_logged
        err_str = str(e)
        if "insufficient_quota" in err_str or "429" in err_str:
            if not _quota_error_logged:
                _quota_error_logged = True
                global _use_fallback_tts
                _use_fallback_tts = True
                _report_error(
                    "⚠️ OpenAI quota exceeded — switching to Windows built-in voice.\n"
                    "Add credits at platform.openai.com/billing to restore the AI voice."
                )
        elif "401" in err_str or "invalid_api_key" in err_str:
            _report_error("❌ Invalid OpenAI API key — check your key in ⚙ API Keys.")
            _speak_fallback(text)
        elif "insufficient_quota" in err_str or "429" in err_str:
            # already logged above — use fallback so app still works
            _speak_fallback(text)
        else:
            # transient error — try fallback silently
            _speak_fallback(text)


def speak(text: str):
    """Speak text aloud — OpenAI gpt-4o-mini-tts if available, else Windows TTS."""
    if _use_fallback_tts:
        threading.Thread(target=_speak_fallback, args=(text,), daemon=True).start()
    else:
        threading.Thread(target=_speak_openai, args=(text,), daemon=True).start()


def stop_speaking():
    """Interrupt current speech (barge-in)."""
    global _speaking
    _barge_in_event.set()
    _speaking = False


def is_speaking() -> bool:
    return _speaking


# ── VAD-based recording ───────────────────────────────────────────────────────

def _rms(data: np.ndarray) -> float:
    return float(np.sqrt(np.mean(data.astype(np.float32) ** 2))) / 32768.0


def listen_vad(silence_duration: float = None, max_seconds: float = None):
    """
    Record using VAD — starts on speech, stops after silence.
    Returns raw PCM bytes (16kHz mono int16) or None.
    """
    sr_val = settings["samplerate"]
    threshold = settings["vad_threshold"]
    sil_dur = silence_duration or settings["silence_duration"]
    max_sec = max_seconds or settings["max_record_seconds"]

    chunk_size = int(sr_val * 0.1)
    frames = []
    recording = False
    silent_chunks = 0
    silence_chunks_needed = int(sil_dur / 0.1)
    max_chunks = int(max_sec / 0.1)
    total_chunks = 0

    device = settings["microphone_device"]
    global _vad_active
    _vad_active = True
    try:
        with sd.InputStream(samplerate=sr_val, channels=1, dtype="int16",
                            blocksize=chunk_size, device=device) as stream:
            while total_chunks < max_chunks:
                chunk, _ = stream.read(chunk_size)
                rms = _rms(chunk)
                if _level_cb:
                    try:
                        _level_cb(rms)
                    except Exception:
                        pass

                if not recording:
                    if rms > threshold:
                        recording = True
                        frames.append(chunk.copy())
                        silent_chunks = 0
                        # Notify UI that voice capture has started
                        if _recording_state_cb:
                            try:
                                _recording_state_cb(True)
                            except Exception:
                                pass
                        # Barge-in: interrupt TTS if user starts talking
                        if _speaking:
                            stop_speaking()
                else:
                    frames.append(chunk.copy())
                    if rms < threshold:
                        silent_chunks += 1
                        if silent_chunks >= silence_chunks_needed:
                            break
                    else:
                        silent_chunks = 0
                    total_chunks += 1
    finally:
        _vad_active = False

    # Notify UI that recording has ended
    if _recording_state_cb:
        try:
            _recording_state_cb(False)
        except Exception:
            pass
    if _level_cb:
        try:
            _level_cb(0.0)
        except Exception:
            pass
    if not frames or len(frames) < 3:
        return None
    return np.concatenate(frames, axis=0).tobytes()


# ── Speech-to-text ────────────────────────────────────────────────────────────

def _write_wav(file_obj, pcm_bytes: bytes):
    with wave.open(file_obj, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(settings["samplerate"])
        wf.writeframes(pcm_bytes)


def _transcribe_openai(audio_bytes: bytes) -> str:
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key or api_key == "your_openai_key_here":
        return _transcribe_google(audio_bytes)
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            tmp_path = f.name
            _write_wav(f, audio_bytes)
        with open(tmp_path, "rb") as f:
            result = client.audio.transcriptions.create(
                model="whisper-1", file=f, language="en",
            )
        os.unlink(tmp_path)
        return result.text.strip()
    except Exception:
        return _transcribe_google(audio_bytes)


def _transcribe_google(audio_bytes: bytes) -> str:
    recognizer = sr.Recognizer()
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        tmp_path = f.name
        _write_wav(f, audio_bytes)
    try:
        with sr.AudioFile(tmp_path) as source:
            audio = recognizer.record(source)
        return recognizer.recognize_google(audio).strip()
    except Exception:
        return ""
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


def listen(timeout: int = 6, phrase_limit: int = 15) -> str:
    """VAD record + Whisper transcribe. Returns text or empty string."""
    audio_bytes = listen_vad(
        silence_duration=settings["silence_duration"],
        max_seconds=phrase_limit,
    )
    if not audio_bytes:
        return ""
    # Check cost limit before calling paid API
    if _cost and _cost.is_over_limit():
        _speak_windows("Daily spending limit reached. Using free speech recognition.")
        return _transcribe_google(audio_bytes)
    api_key = os.getenv("OPENAI_API_KEY", "")
    if api_key and api_key != "your_openai_key_here":
        # Log Whisper cost — duration = bytes / (samplerate * 2 bytes per int16 sample)
        duration_sec = len(audio_bytes) / (settings["samplerate"] * 2)
        if _cost:
            _cost.log_whisper(duration_sec)
        return _transcribe_openai(audio_bytes)
    return _transcribe_google(audio_bytes)


# ── Wake-word detection (free — Google STT, no API cost) ──────────────────────

WAKE_WORDS = ["hey girl", "hey, girl", "hey gurl", "ok girl", "hi girl"]


def listen_for_wake_word(timeout: float = 2.5) -> bool:
    """
    Short listen — returns True if a wake word is heard.
    Uses free Google STT so Whisper is only invoked after wake word.
    """
    recognizer = sr.Recognizer()
    recognizer.energy_threshold = 300
    recognizer.dynamic_energy_threshold = True
    try:
        mic_index = settings["microphone_device"]
        mic_kwargs = {"device_index": mic_index} if mic_index is not None else {}
        with sr.Microphone(**mic_kwargs) as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.2)
            try:
                audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=3)
            except sr.WaitTimeoutError:
                return False
        text = recognizer.recognize_google(audio).lower()
        return any(kw in text for kw in WAKE_WORDS)
    except (sr.UnknownValueError, sr.RequestError, OSError):
        return False


if __name__ == "__main__":
    speak("Hello, I am ready.")
    time.sleep(2)
    print("Listening...")
    result = listen()
    print(f"You said: {result}")
    if result:
        speak(f"You said: {result}")
        time.sleep(3)
