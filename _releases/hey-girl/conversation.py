"""
Conversation Memory
Maintains full session history for multi-turn conversations.
Passed to Claude so it remembers context across messages.
"""

import json
import os
from datetime import datetime

HISTORY_FILE = "conversation_history.json"
MAX_MESSAGES = 40  # keep last 40 exchanges in memory


class ConversationMemory:
    def __init__(self):
        self._messages: list[dict] = []
        self._load()

    def add(self, role: str, content: str):
        """Add a message. role = 'user' or 'assistant'."""
        self._messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
        })
        # Trim to max
        if len(self._messages) > MAX_MESSAGES:
            self._messages = self._messages[-MAX_MESSAGES:]
        self._save()

    def get_for_api(self) -> list[dict]:
        """Return messages in Anthropic API format (no timestamp)."""
        return [{"role": m["role"], "content": m["content"]} for m in self._messages]

    def clear(self):
        self._messages = []
        self._save()

    def _save(self):
        with open(HISTORY_FILE, "w") as f:
            json.dump(self._messages, f, indent=2)

    def _load(self):
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE) as f:
                    self._messages = json.load(f)
            except Exception:
                self._messages = []

    def summary(self) -> str:
        if not self._messages:
            return "No conversation history."
        lines = []
        for m in self._messages[-10:]:
            ts = m.get("timestamp", "")[:19]
            lines.append(f"[{ts}] {m['role']}: {m['content'][:80]}")
        return "\n".join(lines)


# Singleton
memory = ConversationMemory()
