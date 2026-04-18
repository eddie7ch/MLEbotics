"""
Cost Tracker
Tracks API usage and estimated costs. Enforces daily limits.
"""

import json
import os
from datetime import datetime, date

COST_FILE = "cost_tracker.json"

# Approximate costs per unit (USD)
COSTS = {
    "whisper_per_min":      0.006,   # $0.006 per minute of audio
    "tts_per_1k_chars":     0.015,   # tts-1: $0.015 per 1k characters
    "claude_input_per_1m":  3.00,    # claude-3-5-sonnet input per 1M tokens
    "claude_output_per_1m": 15.00,   # claude-3-5-sonnet output per 1M tokens
    "claude_haiku_in":      0.80,    # haiku input per 1M tokens
    "claude_haiku_out":     4.00,    # haiku output per 1M tokens
    "openai_input_per_1m":  2.50,    # gpt-4o input tokens
    "openai_output_per_1m": 10.00,
}

# Default daily limit in USD
DEFAULT_DAILY_LIMIT = 1.00


def _load() -> dict:
    today = str(date.today())
    if os.path.exists(COST_FILE):
        try:
            with open(COST_FILE) as f:
                data = json.load(f)
            if data.get("date") != today:
                data = _fresh(today)
        except Exception:
            data = _fresh(today)
    else:
        data = _fresh(today)
    return data


def _fresh(today: str) -> dict:
    return {
        "date": today,
        "total_usd": 0.0,
        "daily_limit_usd": DEFAULT_DAILY_LIMIT,
        "events": [],
        "whisper_minutes": 0.0,
        "tts_chars": 0,
        "claude_calls": 0,
        "openai_calls": 0,
    }


def _save(data: dict):
    with open(COST_FILE, "w") as f:
        json.dump(data, f, indent=2)


def get_daily_limit() -> float:
    return _load().get("daily_limit_usd", DEFAULT_DAILY_LIMIT)


def set_daily_limit(usd: float):
    data = _load()
    data["daily_limit_usd"] = usd
    _save(data)


def get_today_total() -> float:
    return _load().get("total_usd", 0.0)


def is_over_limit() -> bool:
    data = _load()
    return data["total_usd"] >= data["daily_limit_usd"]


def log_whisper(audio_seconds: float):
    cost = (audio_seconds / 60.0) * COSTS["whisper_per_min"]
    _add("whisper", cost, f"{audio_seconds:.1f}s audio")


def log_tts(text: str):
    chars = len(text)
    cost = (chars / 1000.0) * COSTS["tts_per_1k_chars"]
    _add("tts", cost, f"{chars} chars")


def log_claude(input_tokens: int, output_tokens: int, model: str = "sonnet"):
    if "haiku" in model:
        cost = (input_tokens / 1e6) * COSTS["claude_haiku_in"] + \
               (output_tokens / 1e6) * COSTS["claude_haiku_out"]
    else:
        cost = (input_tokens / 1e6) * COSTS["claude_input_per_1m"] + \
               (output_tokens / 1e6) * COSTS["claude_output_per_1m"]
    _add("claude", cost, f"{input_tokens}in/{output_tokens}out")


def log_openai_agent(input_tokens: int, output_tokens: int):
    cost = (input_tokens / 1e6) * COSTS["openai_input_per_1m"] + \
           (output_tokens / 1e6) * COSTS["openai_output_per_1m"]
    _add("openai_cua", cost, f"{input_tokens}in/{output_tokens}out")


def _add(source: str, cost: float, detail: str):
    data = _load()
    data["total_usd"] += cost
    data["events"].append({
        "time": datetime.now().strftime("%H:%M:%S"),
        "source": source,
        "cost": round(cost, 5),
        "detail": detail,
    })
    _save(data)


def summary() -> str:
    data = _load()
    total = data["total_usd"]
    limit = data["daily_limit_usd"]
    pct = (total / limit * 100) if limit > 0 else 0
    return (
        f"Today: ${total:.4f} / ${limit:.2f} limit  ({pct:.0f}%)\n"
        f"  Calls: {len(data['events'])} API calls since midnight"
    )


def get_events(n: int = 5) -> list:
    """Return the last n events for today."""
    return _load().get("events", [])[-n:]


def reset_today():
    _save(_fresh(str(date.today())))
