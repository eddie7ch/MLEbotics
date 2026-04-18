"""
Shared Memory / Task Log
Keeps both agents aware of what has been done to avoid conflicts.
"""

import json
import os
from datetime import datetime

LOG_FILE = "agent_memory.json"


def _load() -> list:
    if not os.path.exists(LOG_FILE):
        return []
    with open(LOG_FILE, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []


def _save(events: list):
    with open(LOG_FILE, "w") as f:
        json.dump(events, f, indent=2)


def log_event(agent: str, event_type: str, detail: str):
    """
    Log an agent event to shared memory.

    Args:
        agent: 'claude' or 'openai_cua'
        event_type: e.g. 'start', 'action', 'complete', 'error'
        detail: Description or action string
    """
    events = _load()
    events.append({
        "timestamp": datetime.now().isoformat(),
        "agent": agent,
        "type": event_type,
        "detail": detail,
    })
    _save(events)
    print(f"[Memory] [{agent}] {event_type}: {detail[:80]}")


def get_recent(n: int = 10) -> list:
    """Return the last n events."""
    return _load()[-n:]


def get_summary() -> str:
    """Return a text summary of recent activity for use in agent prompts."""
    events = get_recent(20)
    if not events:
        return "No previous activity."

    lines = []
    for e in events:
        ts = e["timestamp"][11:19]  # HH:MM:SS
        lines.append(f"[{ts}] {e['agent']} -> {e['type']}: {e['detail'][:60]}")
    return "\n".join(lines)


def clear():
    """Clear the memory log."""
    _save([])
    print("[Memory] Cleared.")

# Compatibility: add_to_history alias for log_event
def add_to_history(agent, event_type, detail):
    """Alias for log_event, for legacy code compatibility."""
    log_event(agent, event_type, detail)


if __name__ == "__main__":
    clear()
    log_event("claude", "start", "Clean up File Explorer sidebar")
    log_event("claude", "action", "left_click (120, 450)")
    log_event("claude", "complete", "Clean up File Explorer sidebar")
    log_event("openai_cua", "start", "Search Google for Python tutorials")
    print("\nRecent events:")
    print(get_summary())
