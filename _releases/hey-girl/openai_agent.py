"""
OpenAI Computer Use Agent (CUA)
Handles web-based tasks using OpenAI's computer-use-preview model.
"""

import os
import time
from dotenv import load_dotenv
from openai import OpenAI
from screen import capture_screenshot
from actions import execute_action
from memory import log_event

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

_client = None

def _get_client():
    global _client
    if _client is None:
        if not OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY not set in .env file")
        _client = OpenAI(api_key=OPENAI_API_KEY)
    return _client


SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1080


def run_agent(task: str, max_steps: int = 20):
    """Run the OpenAI CUA agent loop for a given web task."""
    print(f"\n[OpenAI CUA] Starting task: {task}")
    print(f"[OpenAI CUA] Max steps: {max_steps}\n")

    log_event("openai_cua", "start", task)

    client = _get_client()

    # Take initial screenshot
    screenshot_b64 = capture_screenshot()

    # Initial input
    inputs = [
        {
            "type": "computer_call_output",
            "call_id": "initial",
            "acknowledged_safety_checks": [],
            "output": {
                "type": "computer_screenshot",
                "image_url": f"data:image/png;base64,{screenshot_b64}",
            }
        }
    ]

    # Kick off with the task
    response = client.responses.create(
        model="computer-use-preview",
        tools=[{
            "type": "computer_use_preview",
            "display_width": SCREEN_WIDTH,
            "display_height": SCREEN_HEIGHT,
            "environment": "windows",
        }],
        input=[
            {"role": "user", "content": task}
        ],
        truncation="auto",
    )

    for step in range(max_steps):
        print(f"[OpenAI CUA] Step {step + 1}/{max_steps}")

        # Check if done
        if response.status == "completed":
            print("[OpenAI CUA] Task complete.")
            for item in response.output:
                if hasattr(item, "content"):
                    for block in item.content:
                        if hasattr(block, "text"):
                            print(f"[OpenAI CUA] Final: {block.text}")
            log_event("openai_cua", "complete", task)
            break

        # Process computer calls
        computer_calls = [item for item in response.output if item.type == "computer_call"]
        if not computer_calls:
            print("[OpenAI CUA] No computer calls. Ending.")
            break

        new_inputs = []
        for call in computer_calls:
            action = call.action
            print(f"[OpenAI CUA] Action: {action}")
            log_event("openai_cua", "action", str(action))

            # Convert OpenAI action format to our common format
            common_action = _convert_action(action)
            execute_action(common_action)

            time.sleep(0.5)

            new_screenshot_b64 = capture_screenshot()

            new_inputs.append({
                "type": "computer_call_output",
                "call_id": call.call_id,
                "acknowledged_safety_checks": call.pending_safety_checks,
                "output": {
                    "type": "computer_screenshot",
                    "image_url": f"data:image/png;base64,{new_screenshot_b64}",
                }
            })

        response = client.responses.create(
            model="computer-use-preview",
            previous_response_id=response.id,
            tools=[{
                "type": "computer_use_preview",
                "display_width": SCREEN_WIDTH,
                "display_height": SCREEN_HEIGHT,
                "environment": "windows",
            }],
            input=new_inputs,
            truncation="auto",
        )

    print("[OpenAI CUA] Done.")


def _convert_action(action) -> dict:
    """Convert OpenAI CUA action format to our common actions.py format."""
    action_type = action.type

    if action_type == "click":
        button_map = {"left": "left_click", "right": "right_click"}
        return {
            "action": button_map.get(action.button, "left_click"),
            "coordinate": [action.x, action.y],
        }
    elif action_type == "double_click":
        return {"action": "double_click", "coordinate": [action.x, action.y]}
    elif action_type == "move":
        return {"action": "mouse_move", "coordinate": [action.x, action.y]}
    elif action_type == "drag":
        return {
            "action": "left_click_drag",
            "start_coordinate": [action.startX, action.startY],
            "coordinate": [action.endX, action.endY],
        }
    elif action_type == "type":
        return {"action": "type", "text": action.text}
    elif action_type == "key":
        return {"action": "key", "text": action.key}
    elif action_type == "scroll":
        return {
            "action": "scroll",
            "coordinate": [action.x, action.y],
            "direction": action.direction,
            "amount": action.amount,
        }
    elif action_type == "screenshot":
        return {"action": "screenshot"}
    else:
        return {"action": action_type}
