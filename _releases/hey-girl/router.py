"""
Task Router
Classifies a user task as 'desktop' or 'web' to decide which agent handles it.
Uses a lightweight Claude call for smart classification, with keyword fallback.
"""

import os
import re
from dotenv import load_dotenv
import anthropic

load_dotenv()

_client = None

def _get_client():
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    return _client


# Keyword-based fast fallback (no API call needed)
_WEB_KEYWORDS = [
    "browser", "website", "google", "search the web", "open url", "http",
    "youtube", "twitter", "linkedin", "email", "gmail", "outlook web",
    "download from", "navigate to", "go to site", "fill out form", "web form",
    "online", "internet", "reddit", "stackoverflow", "github.com",
]

_DESKTOP_KEYWORDS = [
    "file explorer", "folder", "desktop", "taskbar", "start menu", "settings",
    "control panel", "registry", "unpin", "move file", "rename file", "delete file",
    "open app", "notepad", "calculator", "task manager", "vs code", "terminal",
    "powershell", "cmd", "window", "clipboard", "screenshot", "sidebar",
]


def _keyword_classify(task: str) -> str | None:
    """Quick keyword-based classification. Returns 'web', 'desktop', or None."""
    task_lower = task.lower()
    web_score = sum(1 for kw in _WEB_KEYWORDS if kw in task_lower)
    desktop_score = sum(1 for kw in _DESKTOP_KEYWORDS if kw in task_lower)

    if web_score > desktop_score:
        return "web"
    if desktop_score > web_score:
        return "desktop"
    return None  # ambiguous — escalate to LLM


def _llm_classify(task: str) -> str:
    """Use Claude to classify ambiguous tasks."""
    response = _get_client().messages.create(
        model="claude-3-5-haiku-latest",
        max_tokens=10,
        messages=[{
            "role": "user",
            "content": (
                f'Classify this task as exactly one word — either "desktop" or "web".\n'
                f'"desktop" = local files, apps, OS settings, window management.\n'
                f'"web" = browser, internet, websites, online forms, web search.\n\n'
                f'Task: {task}\n\nAnswer:'
            )
        }]
    )
    text = response.content[0].text.strip().lower()
    return "web" if "web" in text else "desktop"


def classify(task: str) -> str:
    """
    Classify a task as 'desktop' or 'web'.

    Args:
        task: Natural language task description.

    Returns:
        'desktop' or 'web'
    """
    result = _keyword_classify(task)
    if result:
        print(f"[Router] Classified as '{result}' (keyword match)")
        return result

    result = _llm_classify(task)
    print(f"[Router] Classified as '{result}' (LLM classification)")
    return result


if __name__ == "__main__":
    tests = [
        "Clean up my File Explorer sidebar",
        "Search Google for latest Python tutorials",
        "Open VS Code and create a new file",
        "Fill out a job application on LinkedIn",
        "Move all PDFs from Downloads to Documents",
        "Go to GitHub and star a repository",
    ]
    for t in tests:
        print(f"  '{t}' => {classify(t)}")
