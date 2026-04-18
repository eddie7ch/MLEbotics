"""
Hey Girl — Unified Web Server
------------------------------
Combines: Hey Girl Voice AI + Computer Use Agent + AutoFormFiller

Modes:
  CLOUD (Railway / any headless server) — chat + form filler (no desktop control)
  LOCAL (your PC)                       — all features: chat + computer use + voice + form filler

Environment variables:
  ANTHROPIC_API_KEY   — Claude API key
  OPENAI_API_KEY      — OpenAI key
  GITHUB_TOKEN        — GitHub Models token (free GPT-4o)
  GEMINI_API_KEY      — Google Gemini key (free tier for form filling)
  PORT                — Port to listen on (default 5000)
  RAILWAY_ENVIRONMENT — Auto-set by Railway → enables cloud mode
  HEADLESS            — Set to "1" to force cloud mode locally
"""

import os
import sys
import re
import json
import base64
import io
import threading
import logging
from datetime import datetime, date
from pathlib import Path

import requests as http_requests
from flask import Flask, request, jsonify, send_from_directory, Response, stream_with_context
from flask_socketio import SocketIO
from flask_cors import CORS
from dotenv import load_dotenv, set_key

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Mode detection ─────────────────────────────────────────────────────────────
RAILWAY  = bool(os.getenv("RAILWAY_ENVIRONMENT"))
HEADLESS = RAILWAY or os.getenv("HEADLESS", "0") == "1"

# ── App ────────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
app = Flask(__name__, static_folder=str(BASE_DIR / "web"), static_url_path="")
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# ── Shared modules (always available) ─────────────────────────────────────────
sys.path.insert(0, str(BASE_DIR))
from conversation import memory as conv_memory
import cost_tracker

CLAUDE_MODEL   = "claude-3-5-sonnet-20241022"
GITHUB_API_URL = "https://models.inference.ai.azure.com"
GITHUB_MODEL   = "gpt-4o"

# ── Lazy desktop-only import ───────────────────────────────────────────────────
_screen_mod = None

def _get_screen():
    global _screen_mod
    if _screen_mod is None and not HEADLESS:
        try:
            import screen as _s
            _screen_mod = _s
        except Exception:
            pass
    return _screen_mod


# ─────────────────────────────────────────────────────────────────────────────
# Static
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


# ─────────────────────────────────────────────────────────────────────────────
# Status
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/api/status")
def api_status():
    return jsonify({
        "mode":         "cloud" if HEADLESS else "local",
        "computer_use": not HEADLESS,
        "voice":        not HEADLESS,
        "claude":       bool(os.getenv("ANTHROPIC_API_KEY")),
        "openai":       bool(os.getenv("OPENAI_API_KEY")),
        "github":       bool(os.getenv("GITHUB_TOKEN")),
        "version":      "2.0.0",
    })


# ─────────────────────────────────────────────────────────────────────────────
# Chat — regular (used for GPT-4o / GitHub Models)
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/api/chat", methods=["POST"])
def api_chat():
    data          = request.get_json(force=True) or {}
    message       = (data.get("message") or "").strip()
    use_github    = bool(data.get("use_github", False))
    inc_ss        = bool(data.get("include_screenshot", False)) and not HEADLESS

    if not message:
        return jsonify({"error": "Empty message"}), 400

    if cost_tracker.is_over_limit():
        total = cost_tracker.get_today_total()
        limit = cost_tracker.get_daily_limit()
        return jsonify({"error": f"Daily budget limit reached (${total:.4f} / ${limit:.2f})"}), 429

    conv_memory.add("user", message)
    history = conv_memory.get_for_api()[:-1]   # all but the one just added

    screenshot_content = _grab_screenshot_content() if inc_ss else []

    try:
        reply = _chat_github(message, history) if use_github else _chat_claude(message, history, screenshot_content)
    except Exception as e:
        conv_memory._messages.pop()
        return jsonify({"error": str(e)}), 500

    conv_memory.add("assistant", reply)
    return jsonify({"reply": reply, "cost": cost_tracker.get_today_total(), "limit": cost_tracker.get_daily_limit()})


# ─────────────────────────────────────────────────────────────────────────────
# Chat — streaming (Claude only, Server-Sent Events)
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/api/chat/stream", methods=["POST"])
def api_chat_stream():
    data    = request.get_json(force=True) or {}
    message = (data.get("message") or "").strip()
    inc_ss  = bool(data.get("include_screenshot", False)) and not HEADLESS

    if not message:
        return _sse_error("Empty message")

    if cost_tracker.is_over_limit():
        total = cost_tracker.get_today_total()
        limit = cost_tracker.get_daily_limit()
        return _sse_error(f"Daily budget limit reached (${total:.4f} / ${limit:.2f})")

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return _sse_error("ANTHROPIC_API_KEY not configured")

    conv_memory.add("user", message)
    history = conv_memory.get_for_api()[:-1]

    screenshot_content = _grab_screenshot_content() if inc_ss else []
    user_content = screenshot_content + [{"type": "text", "text": message}]
    messages = list(history)
    messages.append({"role": "user", "content": user_content if screenshot_content else message})

    def generate():
        import anthropic as _a
        client      = _a.Anthropic(api_key=api_key)
        full_reply  = []
        try:
            with client.messages.stream(model=CLAUDE_MODEL, max_tokens=2048, messages=messages) as stream:
                for text in stream.text_stream:
                    full_reply.append(text)
                    yield f"data: {json.dumps({'text': text})}\n\n"
                usage = stream.get_final_message().usage
                cost_tracker.log_claude(usage.input_tokens, usage.output_tokens)
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            return

        reply = "".join(full_reply)
        conv_memory.add("assistant", reply)
        yield f"data: {json.dumps({'done': True, 'cost': cost_tracker.get_today_total(), 'limit': cost_tracker.get_daily_limit()})}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _sse_error(msg: str):
    def _gen():
        yield f"data: {json.dumps({'error': msg})}\n\n"
    return Response(stream_with_context(_gen()), mimetype="text/event-stream")


# ─────────────────────────────────────────────────────────────────────────────
# Chat helpers
# ─────────────────────────────────────────────────────────────────────────────

def _grab_screenshot_content() -> list:
    s = _get_screen()
    if not s:
        return []
    try:
        b64 = s.capture_screenshot(resize_to=(1280, 720))
        return [{"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": b64}}]
    except Exception:
        return []


def _chat_claude(message: str, history: list, screenshot_content: list) -> str:
    import anthropic as _a
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not configured")
    client = _a.Anthropic(api_key=api_key)
    user_content = screenshot_content + [{"type": "text", "text": message}]
    messages = list(history)
    messages.append({"role": "user", "content": user_content if screenshot_content else message})
    resp = client.messages.create(model=CLAUDE_MODEL, max_tokens=2048, messages=messages)
    cost_tracker.log_claude(resp.usage.input_tokens, resp.usage.output_tokens)
    return resp.content[0].text


def _chat_github(message: str, history: list) -> str:
    import openai as _oa
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise ValueError("GITHUB_TOKEN not configured")
    client   = _oa.OpenAI(base_url=GITHUB_API_URL, api_key=token)
    messages = []
    for m in history:
        content = m["content"]
        if isinstance(content, list):
            content = " ".join(p.get("text", "") for p in content if isinstance(p, dict) and p.get("type") == "text")
        messages.append({"role": m["role"], "content": content})
    messages.append({"role": "user", "content": message})
    resp = client.chat.completions.create(model=GITHUB_MODEL, messages=messages, max_tokens=2048)
    cost_tracker.log_openai_agent(resp.usage.prompt_tokens, resp.usage.completion_tokens)
    return resp.choices[0].message.content


# ─────────────────────────────────────────────────────────────────────────────
# Computer Use Agent
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/api/agent/run", methods=["POST"])
def api_agent_run():
    if HEADLESS:
        return jsonify({
            "error": "Computer Use requires the app to run locally on your PC. "
                     "Cloud mode supports text chat only."
        }), 503

    data      = request.get_json(force=True) or {}
    task      = (data.get("task") or "").strip()
    agent_type = data.get("agent", "auto")
    max_steps  = min(int(data.get("max_steps", 20)), 50)

    if not task:
        return jsonify({"error": "Empty task"}), 400

    if cost_tracker.is_over_limit():
        return jsonify({"error": "Daily budget limit reached"}), 429

    def _run():
        import builtins
        _orig = builtins.print

        def _sock_print(*args, **kwargs):
            msg = " ".join(str(a) for a in args)
            socketio.emit("agent_log", {"msg": msg, "ts": datetime.now().strftime("%H:%M:%S")})
            _orig(*args, **kwargs)

        builtins.print = _sock_print
        try:
            if agent_type == "openai":
                from openai_agent import run_agent as _fn
                _fn(task, max_steps=max_steps)
            elif agent_type == "auto":
                from router import classify
                kind = classify(task)
                if kind == "web":
                    from openai_agent import run_agent as _fn
                else:
                    from agent import run_agent as _fn
                _fn(task, max_steps=max_steps)
            else:
                from agent import run_agent as _fn
                _fn(task, max_steps=max_steps)
            socketio.emit("agent_done", {"task": task})
        except Exception as e:
            socketio.emit("agent_error", {"error": str(e)})
        finally:
            builtins.print = _orig

    threading.Thread(target=_run, daemon=True).start()
    return jsonify({"status": "started", "task": task})


@app.route("/api/screenshot")
def api_screenshot():
    if HEADLESS:
        return jsonify({"error": "Screenshot not available in cloud mode"}), 503
    s = _get_screen()
    if not s:
        return jsonify({"error": "Screen capture unavailable"}), 503
    try:
        data = s.capture_screenshot(resize_to=(1280, 720))
        return jsonify({"screenshot": data, "ts": datetime.now().isoformat()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# Cost tracker
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/api/cost")
def api_cost():
    d = cost_tracker._load()
    return jsonify({
        "total":           round(d.get("total_usd", 0), 6),
        "limit":           d.get("daily_limit_usd", 1.0),
        "events":          d.get("events", [])[-20:],
        "whisper_minutes": d.get("whisper_minutes", 0),
        "tts_chars":       d.get("tts_chars", 0),
        "claude_calls":    d.get("claude_calls", 0),
        "openai_calls":    d.get("openai_calls", 0),
    })


@app.route("/api/cost/limit", methods=["POST"])
def api_cost_limit():
    val = (request.get_json(force=True) or {}).get("limit")
    if val is None:
        return jsonify({"error": "Missing limit"}), 400
    try:
        cost_tracker.set_daily_limit(float(val))
        return jsonify({"ok": True})
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid value"}), 400


@app.route("/api/cost/reset", methods=["POST"])
def api_cost_reset():
    cost_tracker.reset_today()
    return jsonify({"ok": True})


# ─────────────────────────────────────────────────────────────────────────────
# Conversation history
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/api/history")
def api_history():
    return jsonify({"messages": conv_memory.get_for_api()})


@app.route("/api/history/clear", methods=["POST"])
def api_history_clear():
    conv_memory.clear()
    return jsonify({"ok": True})


# ─────────────────────────────────────────────────────────────────────────────
# Settings — save API keys to .env (local only)
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/api/settings/keys", methods=["POST"])
def api_settings_keys():
    if HEADLESS:
        return jsonify({"error": "Cannot set API keys in cloud mode — use environment variables."}), 403

    data     = request.get_json(force=True) or {}
    env_path = str(BASE_DIR / ".env")

    try:
        if data.get("anthropic"):
            set_key(env_path, "ANTHROPIC_API_KEY", data["anthropic"])
            os.environ["ANTHROPIC_API_KEY"] = data["anthropic"]
        if data.get("openai"):
            set_key(env_path, "OPENAI_API_KEY", data["openai"])
            os.environ["OPENAI_API_KEY"] = data["openai"]
        if data.get("github"):
            set_key(env_path, "GITHUB_TOKEN", data["github"])
            os.environ["GITHUB_TOKEN"] = data["github"]
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# AutoFormFiller — shared helpers
# ─────────────────────────────────────────────────────────────────────────────

ALLOWED_GEMINI_MODELS = {"gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash-lite"}
ALLOWED_CLAUDE_MODELS = {
    "claude-sonnet-4-6", "claude-opus-4-6",
    "claude-sonnet-4-20250514", "claude-opus-4-20250514",
    "claude-haiku-4-5-20251001",
}
ALLOWED_GPT_MODELS  = {"gpt-4o", "gpt-4o-mini", "gpt-4-turbo"}
FREE_TIER_MODEL     = "gemini-1.5-flash"
FREE_TIER_DAILY_LIMIT = 10

_rate_counts: dict = {}
_rate_lock = threading.Lock()

def _check_free_rate_limit(ip: str):
    today = str(date.today())
    with _rate_lock:
        day_map = _rate_counts.setdefault(ip, {})
        for d in list(day_map):
            if d != today:
                del day_map[d]
        if day_map.get(today, 0) >= FREE_TIER_DAILY_LIMIT:
            raise ValueError(
                f"Free tier limit reached ({FREE_TIER_DAILY_LIMIT} fills/day). "
                "Add your own API key in Settings for unlimited use."
            )
        day_map[today] = day_map.get(today, 0) + 1


def _call_ai_for_form(prompt: str, model: str, provided_key: str = "", client_ip: str = "") -> str:
    """Route a form-filling prompt to the correct AI provider."""
    if model in ALLOWED_GEMINI_MODELS:
        import google.generativeai as genai
        key = provided_key or os.getenv("GEMINI_API_KEY", "")
        if not key:
            raise ValueError("No Gemini API key available. Add your own in Settings.")
        if not provided_key:
            _check_free_rate_limit(client_ip or "0.0.0.0")
        genai.configure(api_key=key)
        resp = genai.GenerativeModel(model).generate_content(prompt)
        return resp.text
    elif model in ALLOWED_GPT_MODELS:
        import openai as _oa
        key = provided_key or os.getenv("OPENAI_API_KEY", "")
        if not key:
            raise ValueError("No OpenAI API key. Add yours in Settings.")
        client = _oa.OpenAI(api_key=key)
        resp = client.chat.completions.create(
            model=model, max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.choices[0].message.content
    else:
        import anthropic as _a
        actual = model if model in ALLOWED_CLAUDE_MODELS else "claude-haiku-4-5-20251001"
        key = provided_key or os.getenv("ANTHROPIC_API_KEY", "")
        if not key:
            raise ValueError("No Anthropic API key. Add yours in Settings.")
        client = _a.Anthropic(api_key=key)
        resp = client.messages.create(
            model=actual, max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.content[0].text


def _load_user_data() -> dict:
    config_path = BASE_DIR / "config" / "user_data.json"
    if not config_path.exists():
        config_path = BASE_DIR.parent / "AutoFormFiller" / "config" / "user_data.json"
    if not config_path.exists():
        raise ValueError("config/user_data.json not found.")
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_user_data_file(new_data: dict):
    config_path = BASE_DIR / "config" / "user_data.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    comment = "Fill in your real details. Passwords are handled by Bitwarden — do not add them here."
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            existing = json.load(f)
        comment = existing.get("_comment", comment)
    except Exception:
        pass
    output = {"_comment": comment}
    output.update(new_data)
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)


# ─────────────────────────────────────────────────────────────────────────────
# AutoFormFiller — routes
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/api/fill-form", methods=["POST"])
def api_fill_form():
    try:
        data       = request.get_json(force=True) or {}
        fields     = data.get("fields", [])
        model      = data.get("model", FREE_TIER_MODEL)
        api_key    = data.get("api_key", "")
        client_ip  = request.headers.get("X-Forwarded-For", request.remote_addr or "").split(",")[0].strip()

        if not fields:
            return jsonify({"success": False, "error": "No form fields provided"}), 400

        user_data = _load_user_data()
        prompt = f"""You are a form-filling assistant. Look at these form fields and determine which user data should fill them.

Form fields on the page:
{json.dumps(fields, indent=2)}

Available user data:
{json.dumps(user_data, indent=2)}

For each form field, output a JSON object with:
- "fieldId": the field id/name exactly as provided
- "value": the value to fill (or null if no matching data)
- "reason": brief explanation (max 50 chars)

Output ONLY a valid JSON array. No other text."""

        try:
            result_text = _call_ai_for_form(prompt, model, api_key, client_ip)
        except ValueError as e:
            return jsonify({"success": False, "error": str(e)}), 429 if "limit" in str(e) else 400

        match = re.search(r"\[.*\]", result_text, re.DOTALL)
        if not match:
            return jsonify({"success": False, "error": "AI returned unexpected response"}), 500

        instructions = [i for i in json.loads(match.group()) if i.get("value") is not None]
        return jsonify({"success": True, "instructions": instructions})
    except Exception as e:
        logger.error(f"fill-form error: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/fill-pdf", methods=["POST"])
def api_fill_pdf():
    try:
        from pypdf import PdfReader, PdfWriter
        data       = request.get_json(force=True) or {}
        pdf_url    = data.get("url", "")
        pdf_base64 = data.get("pdf_base64", "")
        model      = data.get("model", FREE_TIER_MODEL)
        api_key    = data.get("api_key", "")
        client_ip  = request.headers.get("X-Forwarded-For", request.remote_addr or "").split(",")[0].strip()

        if pdf_url:
            if pdf_url.startswith("file:///"):
                local_path = pdf_url[8:].replace("/", os.sep)
                with open(local_path, "rb") as f:
                    pdf_bytes = f.read()
            else:
                resp = http_requests.get(pdf_url, timeout=15)
                resp.raise_for_status()
                pdf_bytes = resp.content
        elif pdf_base64:
            pdf_bytes = base64.b64decode(pdf_base64)
        else:
            return jsonify({"success": False, "error": 'Provide "url" or "pdf_base64"'}), 400

        reader     = PdfReader(io.BytesIO(pdf_bytes))
        raw_fields = reader.get_fields()
        if not raw_fields:
            return jsonify({"success": False, "error": "No fillable fields in this PDF"}), 400

        field_list = []
        for name, field in raw_fields.items():
            ft = str(field.get("/FT", "/Tx"))
            if ft not in {"/Tx", "/Ch"}:
                continue
            entry = {"id": name, "label": name, "type": "select" if ft == "/Ch" else "text"}
            if "/Opt" in field:
                entry["options"] = [str(o) for o in field["/Opt"]]
            field_list.append(entry)

        if not field_list:
            return jsonify({"success": False, "error": "No text or choice fields in PDF"}), 400

        user_data = _load_user_data()
        prompt = f"""You are a form-filling assistant. Match PDF fields to user data.

PDF form fields:
{json.dumps(field_list, indent=2)}

Available user data:
{json.dumps(user_data, indent=2)}

Output a JSON array. Each item: {{"fieldId": "...", "value": "..." or null}}
Output ONLY the JSON array. No other text."""

        try:
            result_text = _call_ai_for_form(prompt, model, api_key, client_ip)
        except ValueError as e:
            return jsonify({"success": False, "error": str(e)}), 429 if "limit" in str(e) else 400

        match = re.search(r"\[.*\]", result_text, re.DOTALL)
        if not match:
            return jsonify({"success": False, "error": "AI returned unexpected response"}), 500

        fill_map = {i["fieldId"]: i["value"] for i in json.loads(match.group()) if i.get("value") is not None}
        if not fill_map:
            return jsonify({"success": False, "error": "No matching fields for your data"}), 200

        writer = PdfWriter()
        writer.clone_document_from_reader(reader)
        for page in writer.pages:
            try:
                writer.update_page_form_field_values(page, fill_map)
            except Exception:
                pass

        buf = io.BytesIO()
        writer.write(buf)
        buf.seek(0)
        return jsonify({"success": True, "pdf_base64": base64.b64encode(buf.read()).decode(), "filled_count": len(fill_map)})
    except Exception as e:
        logger.error(f"fill-pdf error: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/get-user-data", methods=["GET"])
def api_get_user_data():
    try:
        data = _load_user_data()
        data.pop("_comment", None)
        return jsonify({"success": True, "data": data})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/save-user-data", methods=["POST"])
def api_save_user_data():
    try:
        new_data = request.get_json(force=True) or {}
        if not isinstance(new_data, dict):
            return jsonify({"success": False, "error": "Expected a JSON object"}), 400
        for key in new_data:
            if not re.match(r"^[a-zA-Z0-9_]+$", key):
                return jsonify({"success": False, "error": f"Invalid field name: {key}"}), 400
        _save_user_data_file(new_data)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/health")
def health():
    return jsonify({"status": "ok", "service": "Hey Girl"})


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def run_server(host: str = "0.0.0.0", port: int = 5000):
    print(f"[Hey Girl] Web server -> http://localhost:{port}")
    print(f"[Hey Girl] Mode: {'CLOUD (chat only)' if HEADLESS else 'LOCAL (full features)'}")
    socketio.run(app, host=host, port=port, allow_unsafe_werkzeug=True)


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    run_server(port=port)
