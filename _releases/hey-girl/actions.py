"""
Input actions module.
Translates Claude's computer use tool actions into real Windows mouse/keyboard events.
Also handles Zoho email actions (read_emails, send_email).
"""

import time
import pyautogui
import subprocess
import zoho_mail

# Safety: fail-safe — move mouse to top-left corner to abort
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.1


def execute_action(action: dict):
    """
    Execute a computer use action returned by Claude.

    Supported actions:
        screenshot       - no-op here (handled in agent loop)
        mouse_move       - move mouse to (x, y)
        left_click       - left click at (x, y)
        right_click      - right click at (x, y)
        double_click     - double click at (x, y)
        left_click_drag  - click and drag from start to end
        type             - type a string
        key              - press a key or combo (e.g. "ctrl+c")
        scroll           - scroll at (x, y)
        cursor_position  - no-op (informational)
    """
    action_type = action.get("action")

    if action_type == "screenshot":
        pass  # handled externally in agent loop

    elif action_type == "mouse_move":
        x, y = action["coordinate"]
        print(f"  -> mouse_move ({x}, {y})")
        pyautogui.moveTo(x, y, duration=0.3)

    elif action_type == "left_click":
        x, y = action["coordinate"]
        print(f"  -> left_click ({x}, {y})")
        pyautogui.click(x, y)

    elif action_type == "right_click":
        x, y = action["coordinate"]
        print(f"  -> right_click ({x}, {y})")
        pyautogui.rightClick(x, y)

    elif action_type == "double_click":
        x, y = action["coordinate"]
        print(f"  -> double_click ({x}, {y})")
        pyautogui.doubleClick(x, y)

    elif action_type == "left_click_drag":
        start = action["start_coordinate"]
        end = action["coordinate"]
        print(f"  -> drag {start} -> {end}")
        pyautogui.mouseDown(start[0], start[1])
        time.sleep(0.1)
        pyautogui.moveTo(end[0], end[1], duration=0.5)
        pyautogui.mouseUp()

    elif action_type == "type":
        text = action.get("text", "")
        print(f"  -> type: {repr(text)}")
        pyautogui.typewrite(text, interval=0.05)

    elif action_type == "key":
        key = action.get("text", "")
        print(f"  -> key: {key}")
        # Convert Claude key format (e.g. "ctrl+c") to pyautogui hotkey
        parts = key.lower().split("+")
        if len(parts) > 1:
            pyautogui.hotkey(*parts)
        else:
            pyautogui.press(parts[0])

    elif action_type == "scroll":
        x, y = action["coordinate"]
        direction = action.get("direction", "down")
        amount = action.get("amount", 3)
        print(f"  -> scroll {direction} x{amount} at ({x}, {y})")
        pyautogui.moveTo(x, y)
        if direction == "up":
            pyautogui.scroll(amount)
        else:
            pyautogui.scroll(-amount)

    elif action_type == "cursor_position":
        pass  # informational only

    # ── Zoho Mail actions ──────────────────────────────────────────────────────

    elif action_type == "read_emails":
        folder = action.get("folder", "INBOX")
        count  = int(action.get("count", 10))
        print(f"  -> read_emails folder={folder} count={count}")
        try:
            emails = zoho_mail.read_emails(folder=folder, count=count)
            action["_result"] = emails
            for i, e in enumerate(emails, 1):
                print(f"     [{i}] {e['date']}  From: {e['from']}  Subject: {e['subject']}")
        except Exception as exc:
            print(f"  [!] read_emails error: {exc}")
            action["_error"] = str(exc)

    elif action_type == "send_email":
        to      = action.get("to", "")
        subject = action.get("subject", "")
        body    = action.get("body", "")
        html    = bool(action.get("html", False))
        print(f"  -> send_email to={to!r} subject={subject!r}")
        try:
            result = zoho_mail.send_email(to=to, subject=subject, body=body, html=html)
            action["_result"] = result
        except Exception as exc:
            print(f"  [!] send_email error: {exc}")
            action["_error"] = str(exc)

    else:
        print(f"  [!] Unknown action type: {action_type}")
