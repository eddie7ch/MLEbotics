"""
Claude Computer Use Agent
Controls your Windows PC autonomously via Claude's API.
"""

import os
import time
import base64
from dotenv import load_dotenv
import anthropic
from screen import capture_screenshot
from actions import execute_action
from memory import log_event
import pyautogui
import re
import threading
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import pyttsx3
import speech_recognition as sr

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
if not ANTHROPIC_API_KEY:
    raise ValueError("ANTHROPIC_API_KEY not set in .env file")

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1080

TOOLS = [
    {
        "type": "computer_20241022",
        "name": "computer",
        "display_width_px": SCREEN_WIDTH,
        "display_height_px": SCREEN_HEIGHT,
        "display_number": 1,
    }
]

SYSTEM_PROMPT = """You are an autonomous PC control agent running on a Windows machine.
You can see the screen and control the mouse and keyboard.
Be precise, cautious, and always confirm before performing irreversible actions.
Take screenshots frequently to verify your actions worked."""


def run_agent(task: str, max_steps: int = 20, history=None):
    """Run the agent loop for a given task."""
    print(f"\n[Agent] Starting task: {task}")
    print(f"[Agent] Max steps: {max_steps}\n")

    log_event("claude", "start", task)
    messages = []

    # Use history for context-aware responses
    if history:
        print("[Agent] Conversation history:")
        for speaker, msg in history[-5:]:
            print(f"{speaker}: {msg}")
    # Example: ask for clarification if command is ambiguous
    if not task.strip():
        return "I didn't catch that. Could you repeat?"
    if "flight" in task.lower() and ("from" not in task.lower() or "to" not in task.lower()):
        return "Please specify both origin and destination for the flight search."

    # Take initial screenshot
    screenshot_b64 = capture_screenshot()

    messages.append({
        "role": "user",
        "content": [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": screenshot_b64,
                },
            },
            {
                "type": "text",
                "text": f"Task: {task}\n\nHere is the current state of the screen. Please complete the task."
            }
        ],
    })

    for step in range(max_steps):
        print(f"[Agent] Step {step + 1}/{max_steps}")

        response = client.beta.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=4096,
            tools=TOOLS,
            messages=messages,
            betas=["computer-use-2024-10-22"],
            system=SYSTEM_PROMPT,
        )

        print(f"[Agent] Stop reason: {response.stop_reason}")

        # Append assistant response
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            print("[Agent] Task complete.")
            for block in response.content:
                if hasattr(block, "text"):
                    print(f"[Agent] Final message: {block.text}")
            log_event("claude", "complete", task)
            break

        # Process tool calls
        tool_results = []
        for block in response.content:
            if block.type == "tool_use" and block.name == "computer":
                action = block.input
                print(f"[Agent] Action: {action}")
                log_event("claude", "action", str(action))

                # Execute the action
                execute_action(action)

                # Small delay to let UI settle
                time.sleep(0.5)

                # Take new screenshot after action
                new_screenshot_b64 = capture_screenshot()

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": new_screenshot_b64,
                            },
                        }
                    ],
                })

        if tool_results:
            messages.append({"role": "user", "content": tool_results})
        else:
            print("[Agent] No tool calls returned. Ending loop.")
            break

    print("[Agent] Done.")


def perform_automation(action, params=None):
    """Perform mouse/keyboard automation based on action and parameters."""
    if action == "move_mouse":
        x, y = params.get("x"), params.get("y")
        pyautogui.moveTo(x, y)
    elif action == "click":
        pyautogui.click()
    elif action == "type":
        text = params.get("text", "")
        pyautogui.typewrite(text)
    elif action == "press_key":
        key = params.get("key")
        pyautogui.press(key)
    elif action == "scroll":
        amount = params.get("amount", 0)
        pyautogui.scroll(amount)
    elif action == "hotkey":
        keys = params.get("keys", [])
        pyautogui.hotkey(*keys)
    elif action == "screenshot":
        filename = params.get("filename", "screenshot.png")
        pyautogui.screenshot(filename)
        print(f"Screenshot saved to {filename}")
    else:
        print(f"Unknown automation action: {action}")


def search_flights(origin, destination, date):
    """Automate flight search using Selenium (example: Google Flights)."""
    driver = webdriver.Chrome()
    driver.get("https://www.google.com/flights")
    # This is a simplified example; selectors may change over time
    try:
        # Enter origin
        origin_input = driver.find_element(By.XPATH, '//input[@placeholder="Where from?"]')
        origin_input.clear()
        origin_input.send_keys(origin)
        origin_input.send_keys(Keys.ENTER)
        # Enter destination
        dest_input = driver.find_element(By.XPATH, '//input[@placeholder="Where to?"]')
        dest_input.clear()
        dest_input.send_keys(destination)
        dest_input.send_keys(Keys.ENTER)
        # Enter date (not implemented: would require more selectors)
        # ...
        print(f"Searching flights from {origin} to {destination} on {date}")
    except Exception as e:
        print(f"Flight search failed: {e}")
    # driver.quit()  # Uncomment to close browser after search


# Voice output (TTS)
_tts_engine = None
def speak(text):
    global _tts_engine
    print(f"[Hey Girl] {text}")
    try:
        if _tts_engine is None:
            _tts_engine = pyttsx3.init()
            voices = _tts_engine.getProperty('voices')
            # Prefer a female voice if available
            for v in voices:
                if 'female' in v.name.lower() or 'zira' in v.name.lower() or 'hazel' in v.name.lower():
                    _tts_engine.setProperty('voice', v.id)
                    break
            _tts_engine.setProperty('rate', 175)
        _tts_engine.say(text)
        _tts_engine.runAndWait()
    except Exception as e:
        print(f"[TTS error] {e}")

# Voice input (STT)
def listen(timeout=5, phrase_limit=10):
    recognizer = sr.Recognizer()
    recognizer.dynamic_energy_threshold = True
    with sr.Microphone() as source:
        recognizer.adjust_for_ambient_noise(source, duration=0.5)
        print("Listening...")
        try:
            audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_limit)
        except sr.WaitTimeoutError:
            return ""
    try:
        return recognizer.recognize_google(audio)
    except sr.UnknownValueError:
        return ""
    except sr.RequestError as e:
        print(f"Speech recognition error: {e}")
        return ""

# Web search using DuckDuckGo Instant Answer API (no key needed)
def web_search(query: str) -> str:
    try:
        resp = requests.get(
            "https://api.duckduckgo.com/",
            params={"q": query, "format": "json", "no_html": "1", "skip_disambig": "1"},
            timeout=8
        )
        data = resp.json()
        answer = data.get("AbstractText") or data.get("Answer") or ""
        if not answer:
            related = data.get("RelatedTopics", [])
            if related and isinstance(related[0], dict):
                answer = related[0].get("Text", "")
        return answer if answer else f"No instant answer found for: {query}"
    except Exception as e:
        return f"Web search error: {e}"

# Always-on wake word listener — runs in background thread
_wake_word = "hey girl"
_wake_listener_running = False
_command_callback = None

def _wake_word_loop():
    global _wake_listener_running
    recognizer = sr.Recognizer()
    recognizer.dynamic_energy_threshold = True
    print(f"[Hey Girl] Always-on listening active. Say '{_wake_word}' to activate.")
    while _wake_listener_running:
        try:
            with sr.Microphone() as source:
                recognizer.adjust_for_ambient_noise(source, duration=0.3)
                audio = recognizer.listen(source, timeout=3, phrase_time_limit=6)
            text = recognizer.recognize_google(audio).lower()
            print(f"[Wake] Heard: {text}")
            if _wake_word in text:
                command = text.replace(_wake_word, "").strip()
                if not command:
                    speak("Yes? How can I help you?")
                    command = listen(timeout=8, phrase_limit=15)
                if command and _command_callback:
                    _command_callback(command)
        except (sr.WaitTimeoutError, sr.UnknownValueError):
            pass
        except sr.RequestError as e:
            print(f"[Wake listener] STT error: {e}")
        except Exception as e:
            print(f"[Wake listener] Error: {e}")

def start_wake_listener(callback):
    """Start the always-on wake word listener in a background thread."""
    global _wake_listener_running, _command_callback
    _command_callback = callback
    _wake_listener_running = True
    t = threading.Thread(target=_wake_word_loop, daemon=True)
    t.start()
    return t

def stop_wake_listener():
    global _wake_listener_running
    _wake_listener_running = False

if __name__ == "__main__":
    task = input("Enter task for Claude to perform on your PC: ").strip()
    run_agent(task)
