"""
Claude PC Control — Windows GUI App
One-click interface for the dual-agent desktop/web control system.
"""

import sys
import os
import math
import base64
import threading
import queue
import ctypes
import tkinter as tk

# ── Tell Windows this is "Hey Girl", not python.exe — fixes taskbar grouping ──
try:
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("HeyGirl.App")
except Exception:
    pass
from tkinter import scrolledtext, filedialog, messagebox
import customtkinter as ctk
from dotenv import load_dotenv, set_key
from voice import (listen, speak, stop_speaking, is_speaking,
                   settings as voice_settings, OPENAI_VOICES, VOICE_PRESETS,
                   listen_for_wake_word, get_input_devices,
                   set_recording_state_callback, set_level_callback,
                   set_error_callback,
                   start_level_monitor, stop_level_monitor)
import anthropic
from conversation import memory as conv_memory
from screen import capture_screenshot, capture_region
import cost_tracker

load_dotenv()

# ── Model config (update here when Anthropic releases new versions) ────────────
CLAUDE_MODEL = "claude-3-5-sonnet-20241022"
GITHUB_API_URL = "https://models.inference.ai.azure.com"
GITHUB_MODEL   = "gpt-4o"
# ── Theme ──────────────────────────────────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ── Log queue for thread-safe UI updates ──────────────────────────────────────
log_queue = queue.Queue()

# ── Redirect stdout/stderr to the log queue ───────────────────────────────────
class QueueWriter:
    def __init__(self, q: queue.Queue):
        self.q = q
    def write(self, text: str):
        if text.strip():
            self.q.put(text)
    def flush(self):
        pass


# ── Main App ──────────────────────────────────────────────────────────────────
class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Hey Girl")
        self.resizable(True, True)

        # Position on the right side of the screen
        self.update_idletasks()
        w, h = 820, 700
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        x = screen_w - w - 10
        y = (screen_h - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.minsize(700, 550)

        self._agent_thread: threading.Thread | None = None
        self._running = False
        self._listening = False
        self._muted = True   # start MUTED — user clicks mic or says Hey Girl to activate
        self._continuous_active = False
        self._screen_context = False  # auto-screenshot disabled; user attaches manually
        self._wake_word_enabled = True  # two-phase listening to save Whisper costs
        self._screen_watch = False    # continuous screen monitoring
        self._last_screen_hash: str = ""
        self._watch_interval = 8      # seconds between watch checks
        self._attached_files: list[dict] = []  # list of {name, content_type, data}
        self._budget_warned_70 = False   # spoken warning flags (reset each session)
        self._budget_warned_90 = False
        self._in_conversation = False     # True = skip wake word until mute is pressed

        self._build_ui()  # mute_btn is built here with correct initial state
        self._load_chat_history()  # restore previous conversation into UI
        self._check_api_keys()
        self._poll_log()
        # Wire mic-activity indicator
        set_recording_state_callback(self._on_recording_state)
        # Wire real-time level meter
        set_level_callback(self._on_level)
        # Wire voice error reporting to the agent log
        set_error_callback(lambda msg: self._log(f"\u274c {msg}"))
        # Show budget immediately on launch
        self._update_cost_display()
        self.after(1000, self._poll_cost)
        # Listening loop is NOT started automatically — click 🎤 or say Hey Girl to begin
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _on_close(self):
        self._continuous_active = False
        self._muted = True
        self.destroy()

    def _load_chat_history(self):
        """Populate the log box with saved conversation history on startup."""
        messages = conv_memory.get_for_api()
        if not messages:
            return
        self._log("─" * 60)
        self._log("  ↑  Previous conversation  ↑")
        self._log("─" * 60)
        for m in messages:
            role = m.get("role", "")
            content = m.get("content", "")
            # content can be a string or a list of parts (multimodal)
            if isinstance(content, list):
                text_parts = [p.get("text", "") for p in content if isinstance(p, dict) and p.get("type") == "text"]
                content = " ".join(text_parts)
            if role == "user":
                self._log(f"🗣 You: {content}")
            elif role == "assistant":
                self._log(f"🤖 Assistant: {content}")
        self._log("─" * 60)

    # ── UI Construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)  # log row expands

        # ── Budget bar ─────────────────────────────────────────────────────────
        budget_bar_frame = ctk.CTkFrame(self, height=54, corner_radius=0, fg_color="#0a0a0a")
        budget_bar_frame.grid(row=0, column=0, sticky="ew")
        budget_bar_frame.grid_columnconfigure(1, weight=1)
        budget_bar_frame.bind("<Button-1>", lambda e: self._open_voice_settings())

        # Row 0 — progress bar + totals
        ctk.CTkLabel(
            budget_bar_frame, text="💰 Daily Budget",
            font=ctk.CTkFont(size=11, weight="bold"), text_color="#888",
        ).grid(row=0, column=0, padx=(12, 8), pady=(6, 2), sticky="w")

        self.budget_progress = ctk.CTkProgressBar(
            budget_bar_frame, height=10, corner_radius=4,
            progress_color="#388e3c", fg_color="#222",
        )
        self.budget_progress.set(0)
        self.budget_progress.grid(row=0, column=1, padx=(0, 10), pady=(6, 2), sticky="ew")

        self.budget_detail_label = ctk.CTkLabel(
            budget_bar_frame, text="$0.0000 / $1.00",
            font=ctk.CTkFont(size=11), text_color="#888", width=170,
        )
        self.budget_detail_label.grid(row=0, column=2, padx=(0, 8), pady=(6, 2), sticky="e")

        click_hint = ctk.CTkLabel(
            budget_bar_frame, text="(click to adjust)",
            font=ctk.CTkFont(size=10), text_color="#444",
        )
        click_hint.grid(row=0, column=3, padx=(0, 12), pady=(6, 2), sticky="e")

        # Row 1 — live recent-calls ticker
        self.live_calls_label = ctk.CTkLabel(
            budget_bar_frame, text="No API calls yet this session",
            font=ctk.CTkFont(family="Consolas", size=10), text_color="#444",
            anchor="w",
        )
        self.live_calls_label.grid(row=1, column=0, columnspan=4, padx=12, pady=(0, 5), sticky="ew")

        # Make all budget bar children clickable too
        for child in budget_bar_frame.winfo_children():
            child.bind("<Button-1>", lambda e: self._open_voice_settings())

        # API key status bar
        self.status_bar = ctk.CTkFrame(self, height=36, corner_radius=0, fg_color="#111")
        self.status_bar.grid(row=1, column=0, sticky="ew")
        self.status_bar.grid_columnconfigure((0, 1, 2), weight=1)

        self.claude_status = ctk.CTkLabel(self.status_bar, text="", font=ctk.CTkFont(size=12))
        self.claude_status.grid(row=0, column=0, padx=16, pady=6, sticky="w")

        self.openai_status = ctk.CTkLabel(self.status_bar, text="", font=ctk.CTkFont(size=12))
        self.openai_status.grid(row=0, column=1, padx=16, pady=6, sticky="w")

        settings_btn = ctk.CTkButton(
            self.status_bar, text="⚙ API Keys", width=100, height=24,
            font=ctk.CTkFont(size=11), fg_color="#333", hover_color="#555",
            command=self._open_settings,
        )
        settings_btn.grid(row=0, column=2, padx=16, pady=6, sticky="e")

        voice_btn = ctk.CTkButton(
            self.status_bar, text="🔊 Voice", width=80, height=24,
            font=ctk.CTkFont(size=11), fg_color="#333", hover_color="#555",
            command=self._open_voice_settings,
        )
        voice_btn.grid(row=0, column=3, padx=(0, 4), pady=6, sticky="e")


        # Task input area
        input_frame = ctk.CTkFrame(self, fg_color="#111", corner_radius=0)
        input_frame.grid(row=3, column=0, sticky="ew", padx=0, pady=(0, 0))
        input_frame.grid_columnconfigure(0, weight=1)

        # Full-width multi-line text box
        self.task_entry = ctk.CTkTextbox(
            input_frame,
            height=72,
            font=ctk.CTkFont(size=13),
            fg_color="#1a1a1a",
            text_color="#e0e0e0",
            border_color="#333",
            border_width=1,
            wrap="word",
        )
        self.task_entry.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 0))
        # Insert placeholder manually (CTkTextbox has no placeholder_text)
        self._entry_placeholder = "Ask Hey Girl anything, or give a command…  (Enter = send, Shift+Enter = new line)"
        self.task_entry.insert("1.0", self._entry_placeholder)
        self.task_entry._textbox.configure(foreground="#555")
        def _on_focus_in(e):
            cur = self.task_entry.get("1.0", "end-1c")
            if cur == self._entry_placeholder:
                self.task_entry.delete("1.0", "end")
                self.task_entry._textbox.configure(foreground="#e0e0e0")
        def _on_focus_out(e):
            if not self.task_entry.get("1.0", "end-1c").strip():
                self.task_entry.delete("1.0", "end")
                self.task_entry.insert("1.0", self._entry_placeholder)
                self.task_entry._textbox.configure(foreground="#555")
        self.task_entry.bind("<FocusIn>", _on_focus_in)
        self.task_entry.bind("<FocusOut>", _on_focus_out)
        # Enter = send, Shift+Enter = real newline
        def _on_return(e):
            self._run_task()
            return "break"   # prevent newline
        self.task_entry.bind("<Return>", _on_return)
        self.task_entry.bind("<Shift-Return>", lambda e: None)  # allow newline

        # Buttons row — sits directly below the text box
        btn_row = ctk.CTkFrame(input_frame, fg_color="transparent")
        btn_row.grid(row=1, column=0, sticky="ew", padx=12, pady=(6, 0))

        self.run_btn = ctk.CTkButton(
            btn_row,
            text="▶  Run",
            width=110,
            height=36,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#1565C0",
            hover_color="#1976D2",
            command=self._run_task,
        )
        self.run_btn.pack(side="left", padx=(0, 8))

        self.stop_btn = ctk.CTkButton(
            btn_row,
            text="⏹  Stop",
            width=110,
            height=36,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#b71c1c",
            hover_color="#c62828",
            command=self._stop_task,
            state="disabled",
        )
        self.stop_btn.pack(side="left", padx=(0, 8))

        self.mute_btn = ctk.CTkButton(
            btn_row,
            text="🎤  Listening",
            width=130,
            height=36,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#1b5e20",
            hover_color="#2e7d32",
            command=self._toggle_mute,
        )
        self.mute_btn.pack(side="left", padx=(0, 8))

        # ── VU meter — live mic level bar ─────────────────────────────────────
        _NUM_BARS  = 12
        _BAR_W     = 6
        _BAR_GAP   = 2
        _BAR_H     = 18
        _METER_W   = _NUM_BARS * (_BAR_W + _BAR_GAP) - _BAR_GAP + 4
        self._vu_num_bars = _NUM_BARS
        self._vu_bar_w    = _BAR_W
        self._vu_bar_gap  = _BAR_GAP
        self._vu_bar_h    = _BAR_H
        self._vu_lit      = 0   # currently lit bars

        import tkinter as tk
        self.vu_canvas = tk.Canvas(
            btn_row, width=_METER_W, height=_BAR_H + 4,
            bg="#111", highlightthickness=0,
        )
        self.vu_canvas.pack(side="left", padx=(4, 0))
        # Pre-draw the bars (all dark)
        self._vu_rects = []
        for i in range(_NUM_BARS):
            x0 = 2 + i * (_BAR_W + _BAR_GAP)
            rect = self.vu_canvas.create_rectangle(
                x0, 2, x0 + _BAR_W, 2 + _BAR_H,
                fill="#222", outline="",
            )
            self._vu_rects.append(rect)
        ctk.CTkLabel(
            btn_row,
            text='Say "Hey Girl" then speak your request',
            font=ctk.CTkFont(size=11),
            text_color="#607d8b",
        ).pack(side="left", padx=(8, 0))

        # Third row — file upload + snap & read
        file_row = ctk.CTkFrame(input_frame, fg_color="transparent")
        file_row.grid(row=3, column=0, sticky="ew", padx=12, pady=(6, 10))

        self.upload_btn = ctk.CTkButton(
            file_row,
            text="📎  Upload File",
            width=150,
            height=34,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#4527a0",
            hover_color="#512da8",
            command=self._upload_file,
        )
        self.upload_btn.pack(side="left", padx=(0, 8))

        self.snap_btn = ctk.CTkButton(
            file_row,
            text="📷  Screenshot",
            width=148,
            height=34,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#e65100",
            hover_color="#ef6c00",
            command=self._take_screenshot,
        )
        self.snap_btn.pack(side="left", padx=(0, 8))

        self.attached_label = ctk.CTkLabel(
            file_row,
            text="No file attached",
            font=ctk.CTkFont(size=11),
            text_color="#607d8b",
        )
        self.attached_label.pack(side="left", padx=(4, 0))
        # Bind hover preview — must cover outer widget + inner canvas + inner label
        self._img_tooltip: tk.Toplevel | None = None
        self._img_tooltip_hide_id = None
        self._img_tooltip_idx = 0  # which attachment is being previewed
        for _w in (self.attached_label, self.attached_label._canvas, self.attached_label._label):
            _w.bind("<Enter>", self._show_image_tooltip)
            _w.bind("<Leave>", self._schedule_hide_tooltip)

        self.clear_attach_btn = ctk.CTkButton(
            file_row,
            text="✕",
            width=28, height=28,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#37474f", hover_color="#455a64",
            command=self._clear_attachment,
        )
        self.clear_attach_btn.pack(side="left", padx=(4, 0))
        self.clear_attach_btn.pack_forget()  # hidden until file attached

        # Log output
        log_frame = ctk.CTkFrame(self)
        log_frame.grid(row=2, column=0, sticky="nsew", padx=16, pady=(8, 4))
        log_frame.grid_rowconfigure(1, weight=1)
        log_frame.grid_columnconfigure(0, weight=1)

        log_header = ctk.CTkFrame(log_frame, fg_color="transparent")
        log_header.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 4))
        log_header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            log_header, text="Agent Log",
            font=ctk.CTkFont(size=14, weight="bold"), text_color="#4fc3f7",
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkButton(
            log_header, text="Clear Log", width=90, height=28,
            font=ctk.CTkFont(size=12), fg_color="#333", hover_color="#555",
            command=self._clear_log,
        ).grid(row=0, column=1, sticky="e", padx=(0, 6))

        ctk.CTkButton(
            log_header, text="Clear Memory", width=110, height=28,
            font=ctk.CTkFont(size=12), fg_color="#4a1942", hover_color="#6a1b9a",
            command=self._clear_memory,
        ).grid(row=0, column=2, sticky="e")

        self.log_box = ctk.CTkTextbox(
            log_frame,
            font=ctk.CTkFont(family="Consolas", size=13),
            state="disabled",
            wrap="word",
            fg_color="#0d0d0d",
            text_color="#e0e0e0",
        )
        self.log_box.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))

        # Configure color tags on underlying tk.Text widget
        t = self.log_box._textbox
        t.tag_configure("error",   foreground="#ef5350", font=("Consolas", 13, "bold"))
        t.tag_configure("success", foreground="#66bb6a", font=("Consolas", 13, "bold"))
        t.tag_configure("warning", foreground="#ffa726", font=("Consolas", 13))
        t.tag_configure("action",  foreground="#fff176", font=("Consolas", 13))
        t.tag_configure("router",  foreground="#4fc3f7", font=("Consolas", 13))
        t.tag_configure("memory",  foreground="#ce93d8", font=("Consolas", 13))
        t.tag_configure("agent",   foreground="#81d4fa", font=("Consolas", 13))
        t.tag_configure("openai",  foreground="#a5d6a7", font=("Consolas", 13))
        t.tag_configure("divider", foreground="#555555", font=("Consolas", 13))
        t.tag_configure("task",    foreground="#ffffff", font=("Consolas", 14, "bold"))
        t.tag_configure("default", foreground="#e0e0e0", font=("Consolas", 13))
        t.tag_configure("user",    foreground="#f48fb1", font=("Consolas", 13, "bold"))
        t.tag_configure("bot",     foreground="#b39ddb", font=("Consolas", 13, "italic"))

        # Status footer — two labels side by side
        footer_frame = ctk.CTkFrame(self, fg_color="transparent", height=28)
        footer_frame.grid(row=4, column=0, sticky="ew", padx=16, pady=(0, 8))
        footer_frame.grid_columnconfigure(0, weight=1)

        self.footer_label = ctk.CTkLabel(
            footer_frame, text="🔇 Voice off — type below, or click 🔇 to enable voice",
            font=ctk.CTkFont(size=12), text_color="#607d8b",
        )
        self.footer_label.grid(row=0, column=0, sticky="w")

        self.cost_label = ctk.CTkLabel(
            footer_frame, text="", font=ctk.CTkFont(size=11), text_color="#888",
        )
        self.cost_label.grid(row=0, column=1, sticky="e")

    # ── File Upload & Snap & Read ─────────────────────────────────────────────

    def _upload_file(self):
        """Open file picker, read the file, ask Claude to analyze it."""
        path = filedialog.askopenfilename(
            title="Choose a file for Hey Girl to read",
            filetypes=[
                ("Images",          "*.png *.jpg *.jpeg *.gif *.bmp *.webp"),
                ("PDF documents",   "*.pdf"),
                ("Text / Code",     "*.txt *.md *.py *.js *.ts *.cs *.json *.yaml *.yml *.csv *.html *.xml"),
                ("Word documents",  "*.docx"),
                ("All files",       "*.*"),
            ],
        )
        if not path:
            return
        fname = os.path.basename(path)
        self._log(f"📎 Reading file: {fname}")
        threading.Thread(target=self._read_file_worker, args=(path,), daemon=True).start()

    def _read_file_worker(self, path: str):
        try:
            fname = os.path.basename(path)
            ext = os.path.splitext(path)[1].lower()

            if ext in (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"):
                with open(path, "rb") as f:
                    raw = f.read()
                b64 = base64.b64encode(raw).decode()
                mt = {".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                      ".png": "image/png",  ".gif": "image/gif",
                      ".bmp": "image/png",  ".webp": "image/webp"}.get(ext, "image/png")
                self._attached_files = [{"name": fname, "content_type": "image",
                                          "media_type": mt, "data": b64}]
                self.after(0, self._show_file_ask_dialog, fname, None)
                return

            if ext == ".pdf":
                try:
                    import pypdf
                    reader = pypdf.PdfReader(path)
                    text = "\n".join(page.extract_text() or "" for page in reader.pages)
                except ImportError:
                    text = f"[PDF: install pypdf to extract text — file: {fname}]"
                self._attached_files = [{"name": fname, "content_type": "text", "data": text[:12000]}]
                self.after(0, self._show_file_ask_dialog, fname, text[:300])
                return

            if ext == ".docx":
                try:
                    import docx
                    doc = docx.Document(path)
                    text = "\n".join(p.text for p in doc.paragraphs)
                except ImportError:
                    text = f"[DOCX: install python-docx to extract text — file: {fname}]"
                self._attached_files = [{"name": fname, "content_type": "text", "data": text[:12000]}]
                self.after(0, self._show_file_ask_dialog, fname, text[:300])
                return

            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    text = f.read()
            except Exception as e:
                log_queue.put(f"❌ Could not read file: {e}")
                return
            self._attached_files = [{"name": fname, "content_type": "text", "data": text[:12000]}]
            self.after(0, self._show_file_ask_dialog, fname, text[:300])

        except Exception as e:
            log_queue.put(f"❌ File read error: {e}")

    def _show_file_ask_dialog(self, fname: str, preview: str | None):
        """Small dialog: shows file preview, lets user type a question, then sends."""
        win = ctk.CTkToplevel(self)
        win.title(f"Ask about: {fname}")
        win.geometry("540x340")
        win.resizable(False, False)
        win.grab_set()

        ctk.CTkLabel(win, text=f"📎 {fname}",
                     font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(18, 4), padx=20, anchor="w")

        if preview:
            prev_box = ctk.CTkTextbox(win, height=80, font=ctk.CTkFont(family="Consolas", size=11),
                                      fg_color="#111", text_color="#aaa")
            prev_box.pack(fill="x", padx=20, pady=(0, 8))
            prev_box.insert("end", preview + ("…" if len(preview) >= 300 else ""))
            prev_box.configure(state="disabled")

        ctk.CTkLabel(win, text="What do you want to know? (leave blank for full analysis)",
                     font=ctk.CTkFont(size=11), text_color="#888").pack(padx=20, anchor="w")
        question_entry = ctk.CTkEntry(win, height=38, font=ctk.CTkFont(size=13),
                                      placeholder_text="e.g. Summarize this / What are the bugs? / Translate it")
        question_entry.pack(fill="x", padx=20, pady=(4, 12))

        def send():
            question = question_entry.get().strip()
            win.destroy()
            self._send_file_to_claude(question)

        def attach_only():
            win.destroy()
            self.attached_label.configure(text=f"📎 {fname}", text_color="#ce93d8")
            self.clear_attach_btn.pack(side="left", padx=(4, 0))
            self._log(f"📎 File attached: {fname} — included with your next Run or voice command.")

        question_entry.bind("<Return>", lambda e: send())
        btn_row = ctk.CTkFrame(win, fg_color="transparent")
        btn_row.pack(pady=4)
        ctk.CTkButton(btn_row, text="💬 Send & Analyze Now", width=180,
                      fg_color="#4527a0", hover_color="#512da8", command=send).pack(side="left", padx=6)
        ctk.CTkButton(btn_row, text="📌 Attach for Next Run", width=180,
                      fg_color="#333", hover_color="#555", command=attach_only).pack(side="left", padx=6)

    def _send_file_to_claude(self, question: str = ""):
        af = self._attached_files[0] if self._attached_files else None
        if not af:
            return
        gh = os.getenv("GITHUB_TOKEN", "")
        ak = os.getenv("ANTHROPIC_API_KEY", "")
        if not gh and (not ak or ak == "your_anthropic_key_here"):
            self._log("❌ No AI key set — add a GitHub Token or Anthropic key in ⚙ API Keys.")
            return
        prompt = question or (
            f"Please read this file ({af['name']}) carefully and tell me:\n"
            "1. What does it contain / what is it about?\n"
            "2. Key points, data, or important details\n"
            "3. Anything I should know, fix, or act on\n"
            "Be concise but thorough."
        )
        src = "GitHub Copilot" if gh else "Claude"
        self._log(f"📎 Sending '{af['name']}' to {src}… ({question or 'full analysis'})")
        self.upload_btn.configure(state="disabled", text="📎 Reading…")
        threading.Thread(target=self._file_analysis_worker, args=(af, prompt), daemon=True).start()

    def _file_analysis_worker(self, af: dict, prompt: str):
        try:
            if af["content_type"] == "image":
                content = [
                    {"type": "image", "source": {
                        "type": "base64", "media_type": af["media_type"], "data": af["data"]}},
                    {"type": "text", "text": prompt},
                ]
            else:
                content = [{"type": "text",
                            "text": f"{prompt}\n\n--- FILE CONTENT: {af['name']} ---\n{af['data']}"}]
            reply = self._ai_chat(
                messages=[{"role": "user", "content": content}],
                system="You are a helpful file analysis assistant.",
                max_tokens=800,
            )
            conv_memory.add("user", f"[Uploaded file: {af['name']}] {prompt}")
            conv_memory.add("assistant", reply)
            log_queue.put(f"📎 File Analysis — {af['name']}:\n{reply}")
            speak(reply)
        except Exception as e:
            log_queue.put(f"❌ File analysis error: {e}")
        finally:
            self.after(0, self.upload_btn.configure,
                       {"state": "normal", "text": "📎  Upload File"})
            self.after(0, self._clear_attachment)

    def _show_image_tooltip(self, event=None):
        """Show a floating image preview when hovering over the attachment label."""
        # Cancel any pending hide
        if self._img_tooltip_hide_id:
            self.after_cancel(self._img_tooltip_hide_id)
            self._img_tooltip_hide_id = None

        imgs = [f for f in self._attached_files if f.get("content_type") == "image"]
        if not imgs:
            return
        af = imgs[-1]  # preview most recent screenshot
        if self._img_tooltip:
            return  # already showing
        try:
            import base64 as _b64
            from PIL import Image as _Image, ImageTk as _ImageTk
            import io as _io
            raw = _b64.b64decode(af["data"])
            img = _Image.open(_io.BytesIO(raw))
            # Scale to max 420px wide / 300px tall while keeping aspect ratio
            img.thumbnail((420, 300), _Image.LANCZOS)
            tk_img = _ImageTk.PhotoImage(img)

            tip = tk.Toplevel(self)
            tip.overrideredirect(True)
            tip.attributes("-topmost", True)
            tip.configure(bg="#1a1a1a")

            # Border frame
            frame = tk.Frame(tip, bg="#444", padx=2, pady=2)
            frame.pack()
            lbl = tk.Label(frame, image=tk_img, bg="#1a1a1a")
            lbl.image = tk_img  # keep reference
            lbl.pack()
            total = len([f for f in self._attached_files if f.get("content_type") == "image"])
            suffix = f"  ({total} total)" if total > 1 else ""
            tk.Label(frame, text=f"{img.width}\u00d7{img.height}{suffix}",
                     bg="#1a1a1a", fg="#888",
                     font=("Segoe UI", 9)).pack(pady=(2, 4))

            # Position above the label; flip below if too close to top
            self.update_idletasks()
            wx = self.attached_label.winfo_rootx()
            wy = self.attached_label.winfo_rooty()
            th = img.height + 36
            ypos = wy - th - 8
            if ypos < 0:
                ypos = wy + self.attached_label.winfo_height() + 4
            tip.geometry(f"+{wx}+{ypos}")

            self._img_tooltip = tip
            # Hovering into the tooltip itself cancels the hide timer
            for _tw in [tip, frame, lbl]:
                _tw.bind("<Enter>", self._show_image_tooltip)
                _tw.bind("<Leave>", self._schedule_hide_tooltip)
        except Exception as e:
            print(f"Tooltip error: {e}")

    def _schedule_hide_tooltip(self, event=None):
        """Schedule tooltip hide with a short delay to avoid flicker between child widgets."""
        if self._img_tooltip_hide_id:
            self.after_cancel(self._img_tooltip_hide_id)
        self._img_tooltip_hide_id = self.after(120, self._hide_image_tooltip)

    def _hide_image_tooltip(self, event=None):
        self._img_tooltip_hide_id = None
        if self._img_tooltip:
            self._img_tooltip.destroy()
            self._img_tooltip = None

    def _clear_attachment(self):
        if self._img_tooltip_hide_id:
            self.after_cancel(self._img_tooltip_hide_id)
            self._img_tooltip_hide_id = None
        self._hide_image_tooltip()
        self._attached_files = []
        self.attached_label.configure(text="No file attached", text_color="#607d8b")
        self.clear_attach_btn.pack_forget()

    def _take_screenshot(self):
        """Open drag-to-select overlay — no alpha change, no flash at all."""
        self.snap_btn.configure(state="disabled", text="📷 Selecting…")
        self.after(0, self._show_region_selector_blank)

    def _show_region_selector_blank(self):
        """Show a black overlay immediately, then load the real background behind it."""
        import tkinter as tk
        import threading

        with __import__("mss").mss() as sct:
            mon = sct.monitors[0]
            sw, sh = mon["width"], mon["height"]

        # Full-screen black overlay appears instantly — app window untouched, zero flash
        overlay = tk.Toplevel(self)
        overlay.overrideredirect(True)
        overlay.geometry(f"{sw}x{sh}+0+0")
        overlay.attributes("-topmost", True)
        overlay.configure(bg="black")
        overlay.lift()

        canvas = tk.Canvas(overlay, width=sw, height=sh,
                           bg="#111", highlightthickness=0, cursor="crosshair")
        canvas.pack(fill="both", expand=True)

        hint = canvas.create_text(
            sw // 2, 36,
            text="Loading…  •  ESC to cancel",
            fill="#666", font=("Segoe UI", 15, "bold"),
        )

        # Capture the real background in a thread while the black overlay is already on screen
        def _grab_bg():
            from PIL import Image as _Image, ImageTk as _ImageTk
            import mss as _mss
            with _mss.mss() as sct:
                mon = sct.monitors[0]
                raw = sct.grab(mon)
                bg = _Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
            darkened = bg.point(lambda p: int(p * 0.40))
            tk_img = _ImageTk.PhotoImage(darkened)

            def _apply():
                if not overlay.winfo_exists():
                    return
                canvas.create_image(0, 0, anchor="nw", image=tk_img)
                canvas._tk_bg = tk_img  # keep reference
                # Lift selection items above the bg image
                canvas.itemconfig(hint, text="✂  Click and drag to select area    •    ESC to cancel")
                canvas.itemconfig(hint, fill="white")
                canvas.tag_raise(hint)
                # Pass real bg to selector logic
                overlay._bg = bg

            overlay.after(0, _apply)

        threading.Thread(target=_grab_bg, daemon=True).start()

        self._setup_region_selector(overlay, canvas, hint, sw, sh)

    def _show_region_selector(self, bg):
        """Legacy path (kept for compatibility) — delegates to blank-first method."""
        self._show_region_selector_blank()

    def _setup_region_selector(self, overlay, canvas, hint, sw, sh):
        """Wire up mouse events on the overlay. overlay._bg set async by bg thread."""
        from PIL import ImageTk

        CORNER = 14
        state = {"start": None, "items": []}

        def _clear_items():
            for iid in state["items"]:
                try:
                    canvas.delete(iid)
                except Exception:
                    pass
            state["items"] = []

        def _draw_selection(rx1, ry1, rx2, ry2):
            _clear_items()
            items = []
            bg = getattr(overlay, "_bg", None)
            if bg:
                crop = bg.crop((rx1, ry1, rx2, ry2))
                tk_crop = ImageTk.PhotoImage(crop)
                canvas._tk_crop = tk_crop
                items.append(canvas.create_image(rx1, ry1, anchor="nw", image=tk_crop))
            items.append(canvas.create_rectangle(
                rx1 - 1, ry1 - 1, rx2 + 1, ry2 + 1, outline="#000000", width=2))
            items.append(canvas.create_rectangle(
                rx1, ry1, rx2, ry2, outline="#ffffff", width=2, fill=""))
            items.append(canvas.create_rectangle(
                rx1 + 2, ry1 + 2, rx2 - 2, ry2 - 2, outline="#4fc3f7", width=1, fill=""))
            for cx, cy in [(rx1, ry1), (rx2, ry1), (rx1, ry2), (rx2, ry2)]:
                items.append(canvas.create_rectangle(
                    cx - CORNER//2, cy - CORNER//2, cx + CORNER//2, cy + CORNER//2,
                    outline="#000", width=1, fill="#ffffff"))
            w, h = rx2 - rx1, ry2 - ry1
            lx = rx1 + (rx2 - rx1) // 2
            ly = ry2 + 14 if ry2 + 30 < sh else ry1 - 14
            items.append(canvas.create_text(lx+1, ly+1, text=f"{w} × {h}",
                                            fill="#000", font=("Segoe UI", 11, "bold")))
            items.append(canvas.create_text(lx, ly, text=f"{w} × {h}",
                                            fill="#ffffff", font=("Segoe UI", 11, "bold")))
            state["items"] = items

        def on_press(e):
            state["start"] = (e.x, e.y)
            _clear_items()
            canvas.itemconfig(hint, state="hidden")

        def on_drag(e):
            if not state["start"]:
                return
            x1, y1 = state["start"]
            rx1, ry1 = min(x1, e.x), min(y1, e.y)
            rx2, ry2 = max(x1, e.x), max(y1, e.y)
            if rx2 > rx1 and ry2 > ry1:
                _draw_selection(rx1, ry1, rx2, ry2)

        def on_release(e):
            if not state["start"]:
                return
            x1, y1 = state["start"]
            x2, y2 = e.x, e.y
            _clear_items()
            bg = getattr(overlay, "_bg", None)
            overlay.destroy()
            self.lift()
            self.focus_force()
            rx1, ry1 = min(x1, x2), min(y1, y2)
            rx2, ry2 = max(x1, x2), max(y1, y2)
            if rx2 - rx1 < 8 or ry2 - ry1 < 8:
                self._log("⚠ Selection too small — cancelled.")
                self.after(0, self.snap_btn.configure,
                           {"state": "normal", "text": "📷  Screenshot"})
                return
            self.snap_btn.configure(state="normal", text="📷  Screenshot")
            if bg is None:
                self._log("⚠ Background not ready yet — try again.")
                return
            self._log("📷 Capturing… press 📷 again to add more.")
            import io as _io, base64 as _b64
            crop = bg.crop((rx1, ry1, rx2, ry2))
            buf = _io.BytesIO()
            crop.save(buf, format="PNG")
            screenshot_b64 = _b64.b64encode(buf.getvalue()).decode()
            threading.Thread(target=self._attach_region_worker,
                             args=(screenshot_b64,), daemon=True).start()

        def on_escape(e):
            overlay.destroy()
            self.lift()
            self.focus_force()
            self._log("📷 Screenshot cancelled.")
            self.after(0, self.snap_btn.configure,
                       {"state": "normal", "text": "📷  Screenshot"})

        canvas.bind("<ButtonPress-1>",    on_press)
        canvas.bind("<B1-Motion>",         on_drag)
        canvas.bind("<ButtonRelease-1>",  on_release)
        overlay.bind("<Escape>",           on_escape)
        overlay.focus_force()

    def _attach_region_worker(self, screenshot_b64: str):
        try:
            idx = len(self._attached_files) + 1
            self._attached_files.append({"name": f"screenshot_{idx}.png", "content_type": "image",
                                          "media_type": "image/png", "data": screenshot_b64})
            self.after(0, self._update_attached_label)
            n = len(self._attached_files)
            self._log(f"📷 Screenshot {n} ready — press 📷 again to add more, or Enter to analyze all.")
        except Exception as e:
            log_queue.put(f"❌ Screenshot error: {e}")

    def _update_attached_label(self):
        """Refresh the attachment label to reflect current _attached_files list."""
        imgs = [f for f in self._attached_files if f.get("content_type") == "image"]
        others = [f for f in self._attached_files if f.get("content_type") != "image"]
        parts = []
        if imgs:
            parts.append(f"📷 {len(imgs)} screenshot{'s' if len(imgs) > 1 else ''} ready")
        if others:
            parts.append(", ".join(f["name"] for f in others))
        if parts:
            self.attached_label.configure(text="  ".join(parts), text_color="#ef6c00")
            self.clear_attach_btn.pack(side="left", padx=(4, 0))
        else:
            self.attached_label.configure(text="No file attached", text_color="#607d8b")
            self.clear_attach_btn.pack_forget()

    def _screenshot_analyze_worker(self, af_list: list, user_question: str):
        """Directly analyze one or more screenshots using conversation history for smart context."""
        try:
            # Build context from recent conversation history
            recent = conv_memory.get_for_api()[-8:]  # last 8 messages
            context_lines = []
            for m in recent:
                role = m.get("role", "")
                content = m.get("content", "")
                if isinstance(content, list):
                    content = " ".join(p.get("text", "") for p in content
                                      if isinstance(p, dict) and p.get("type") == "text")
                if content.strip():
                    context_lines.append(f"{role}: {content[:200]}")
            context_summary = "\n".join(context_lines)

            n = len(af_list)
            # Smart prompt — either use the user's explicit question or infer from history
            if user_question:
                analysis_prompt = user_question
            elif n > 1:
                analysis_prompt = (
                    f"I've sent you {n} screenshots. Based on our conversation history, "
                    "figure out what I'm most likely comparing or looking for across them. "
                    "Analyze them together — note differences, common issues, or anything important."
                )
            else:
                analysis_prompt = (
                    "Look at this screenshot carefully. Based on our conversation history, "
                    "figure out what I'm most likely looking for and give me a focused, useful analysis.\n"
                    "Cover: what's visible, any issues or key info, and what's relevant to what we were discussing."
                )

            # Build message — all screenshots first, then the prompt
            user_content = []
            for af in af_list:
                user_content.append({"type": "image", "source": {
                    "type": "base64",
                    "media_type": af.get("media_type", "image/png"),
                    "data": af["data"],
                }})
            user_content.append({"type": "text", "text": analysis_prompt})

            system = (
                "You are a smart, direct AI assistant named 'Hey Girl'. "
                + (f"The user has sent you {n} screenshots to analyze together. "
                   if n > 1 else "The user has sent you a screenshot to analyze. ")
                + "Use the conversation history below as context to understand what they are looking for — "
                "don't ask follow-up questions, just give the best analysis you can right away. "
                "Be concise and specific. Max 5-6 sentences unless the user asked for more detail."
                + (f"\n\n--- Recent conversation ---\n{context_summary}" if context_summary else "")
            )

            # Include recent history in the messages for full context
            messages = recent + [{"role": "user", "content": user_content}]

            reply = self._ai_chat(messages=messages, system=system, max_tokens=900)

            label = f"[{n} Screenshots]" if n > 1 else "[Screenshot]"
            conv_memory.add("user", f"{label} {user_question or '(auto-analyze)'}")
            conv_memory.add("assistant", reply)
            log_queue.put(f"📷 Screenshot Analysis ({n} image{'s' if n>1 else ''}):\n{reply}")
            speak(reply)
        except Exception as e:
            log_queue.put(f"❌ Screenshot analysis error: {e}")

    # ── Actions ───────────────────────────────────────────────────────────────

    def _toggle_screen_context(self):
        self._screen_context = not self._screen_context
        if self._screen_context:
            self.screen_ctx_btn.configure(text="🖥 Screen: ON", fg_color="#1a237e", hover_color="#283593")
            self._log("🖥 Screen context ON — AI can see your screen during conversation.")
        else:
            self.screen_ctx_btn.configure(text="🖥 Screen: OFF", fg_color="#37474f", hover_color="#455a64")
            self._log("🖥 Screen context OFF.")

    def _analyze_screen(self, prompt: str = None):
        """Take a screenshot now and ask the AI to describe + help with what it sees."""
        gh = os.getenv("GITHUB_TOKEN", "")
        ak = os.getenv("ANTHROPIC_API_KEY", "")
        if not gh and (not ak or ak == "your_anthropic_key_here"):
            self._log("❌ No AI key set — add a GitHub Token or Anthropic key in ⚙ API Keys.")
            return
        self._log("👁 Capturing screen for analysis…")
        threading.Thread(target=self._analyze_screen_worker, args=(prompt,), daemon=True).start()

    def _analyze_screen_worker(self, prompt: str = None):
        try:
            screenshot_b64 = capture_screenshot()
            user_prompt = prompt or (
                "Please look at my screen carefully and tell me:\n"
                "1. What is currently on the screen?\n"
                "2. Are there any errors, warnings, dialogs or issues I should know about?\n"
                "3. Is there anything I should act on right now?\n"
                "Be concise — 3-5 sentences max."
            )
            reply = self._ai_chat(
                messages=[{"role": "user", "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": screenshot_b64}},
                    {"type": "text", "text": user_prompt},
                ]}],
                system="You are a helpful screen-reading assistant.",
                max_tokens=500,
            )
            log_queue.put(f"👁 Screen Analysis:\n{reply}")
            speak(reply)
        except Exception as e:
            log_queue.put(f"❌ Screen analysis error: {e}")

    def _toggle_screen_watch(self):
        self._screen_watch = not self._screen_watch
        if self._screen_watch:
            self.watch_btn.configure(
                text="📺  Watch Screen: ON",
                fg_color="#1b5e20", hover_color="#2e7d32",
            )
            self._log(f"📺 Screen Watch ON — checking every {self._watch_interval}s for changes.")
            threading.Thread(target=self._screen_watch_loop, daemon=True).start()
        else:
            self.watch_btn.configure(
                text="📺  Watch Screen: OFF",
                fg_color="#37474f", hover_color="#455a64",
            )
            self._log("📺 Screen Watch OFF.")

    def _screen_watch_loop(self):
        """Background loop: take screenshots, hash them, ask AI only when screen changes."""
        import time
        import hashlib
        import base64

        while self._screen_watch:
            time.sleep(self._watch_interval)
            if not self._screen_watch or self._running:
                continue
            try:
                screenshot_b64 = capture_screenshot()
                raw = base64.b64decode(screenshot_b64)
                current_hash = hashlib.md5(raw).hexdigest()
                if current_hash == self._last_screen_hash:
                    continue
                self._last_screen_hash = current_hash

                result = self._ai_chat(
                    messages=[{"role": "user", "content": [
                        {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": screenshot_b64}},
                        {"type": "text", "text": (
                            "You are watching this person's screen silently. "
                            "Only respond if you notice something IMPORTANT they should act on: "
                            "an error dialog, a crash, a security warning, a stuck process, a download finished, "
                            "an installer waiting for input, etc. "
                            "If nothing urgent — reply with exactly: OK\n"
                            "If something needs attention — reply in 1-2 sentences describing it."
                        )},
                    ]}],
                    system="You are a silent screen monitor.",
                    max_tokens=200,
                )
                if result and result != "OK":
                    log_queue.put(f"📺 Screen Watch: {result}")
                    speak(result)
            except Exception as e:
                log_queue.put(f"📺 Watch error: {e}")

    def _toggle_mute(self):
        self._muted = not self._muted
        if self._muted:
            self._in_conversation = False
            self.mute_btn.configure(text="🔇  Voice: OFF", fg_color="#37474f", hover_color="#455a64")
            self.footer_label.configure(text="🔇 Voice off — type below or click 🔇 to talk", text_color="#607d8b")
            stop_level_monitor()
            self._log("🔇 Voice off.")
        else:
            self.mute_btn.configure(text="🎤  Listening", fg_color="#1b5e20", hover_color="#2e7d32")
            self._log("🎤 Voice on. Say \"Hey Girl\" to start talking.")
            # Start the loop on first unmute
            self._start_continuous_listening()
            start_level_monitor()
            self.footer_label.configure(
                text="💤 Waiting for 'Hey Girl'…", text_color="#78909c"
            )

    def _on_level(self, rms: float):
        """Called from voice thread with raw RMS value; updates VU meter on UI thread."""
        # Log scale: maps 0 → 0 bars, ~0.005 → 2 bars, 0.02 (threshold) → 5, 0.1+ → 12
        scaled = math.log1p(rms * 300) / math.log1p(300)  # 0.0 – 1.0
        lit = int(round(scaled * self._vu_num_bars))
        if lit == self._vu_lit:
            return
        self._vu_lit = lit
        self.after(0, self._draw_vu, lit)

    def _draw_vu(self, lit: int):
        n   = self._vu_num_bars
        for i, rect in enumerate(self._vu_rects):
            if i < lit:
                # green → yellow → red gradient
                if i < n * 0.55:
                    color = "#4caf50"
                elif i < n * 0.80:
                    color = "#ffeb3b"
                else:
                    color = "#f44336"
            else:
                color = "#222"
            self.vu_canvas.itemconfig(rect, fill=color)

    def _on_recording_state(self, is_recording: bool):
        """Called from voice thread when VAD starts/stops capturing speech."""
        if is_recording:
            self.after(0, self.footer_label.configure,
                       {"text": "🔴 Hearing you…", "text_color": "#ef5350"})
            self.after(0, self.mute_btn.configure,
                       {"fg_color": "#b71c1c", "text": "🔴  Recording"})
        else:
            # Only reset if we're still in an active listening state
            if not self._muted and not self._running:
                self.after(0, self.footer_label.configure,
                           {"text": "🎤 Listening…", "text_color": "#66bb6a"})
                self.after(0, self.mute_btn.configure,
                           {"fg_color": "#1b5e20", "text": "🎤  Listening"})

    def _start_continuous_listening(self):
        """Kick off the always-on background listening loop (called on first unmute)."""
        if self._continuous_active:
            return  # already running
        self._continuous_active = True
        if self._wake_word_enabled:
            self._log("🎤 Wake word mode ON — say 'Hey Girl' to activate.")
        else:
            self._log("🎤 Always-on voice active.")
        threading.Thread(target=self._continuous_loop, daemon=True).start()

    def _continuous_loop(self):
        """Continuously listen in the background and process speech."""
        import time
        while self._continuous_active:
            # Pause if muted or agent is running
            if self._muted or self._running:
                time.sleep(0.5)
                continue

            # ── Wake-word phase (free Google STT) ────────────────────────────
            if self._wake_word_enabled and not self._in_conversation:
                self.after(0, self.footer_label.configure,
                           {"text": "💤 Waiting for 'Hey Girl'…", "text_color": "#78909c"})
                heard = listen_for_wake_word(timeout=3.0)
                if not heard:
                    continue
                # Wake word detected — enter conversation mode
                self._in_conversation = True
                self.after(0, self.footer_label.configure,
                           {"text": "🎤 Listening…", "text_color": "#66bb6a"})
                self._log("🔔 Wake word detected!")
                speak("Yes?")
                time.sleep(0.5)  # let "Yes?" finish
            else:
                self.after(0, self.footer_label.configure,
                           {"text": "🎤 Listening…", "text_color": "#66bb6a"})

            # ── Check cost limit ─────────────────────────────────────────────
            if cost_tracker.is_over_limit():
                limit = cost_tracker.get_daily_limit()
                self._log(f"⚠ Daily spending limit ${limit:.2f} reached — using free speech recognition only.")
                self.after(0, self.footer_label.configure,
                           {"text": f"⚠ Cost limit ${limit:.2f} reached", "text_color": "#ffa726"})

            # ── Full transcription (Whisper or free fallback) ─────────────────
            text = listen(timeout=5, phrase_limit=20)
            if not text:
                # No speech heard — if we've been waiting too long in conversation
                # mode, quietly exit conversation so we don't keep nagging/listening
                if self._in_conversation:
                    self._silence_count = getattr(self, "_silence_count", 0) + 1
                    if self._silence_count >= 2:
                        # User didn't respond — go back to waiting for wake word silently
                        self._in_conversation = False
                        self._silence_count = 0
                        self.after(0, self.footer_label.configure,
                                   {"text": "💤 Waiting for 'Hey Girl'…", "text_color": "#78909c"})
                else:
                    self._silence_count = 0
                continue
            self._silence_count = 0  # reset on successful speech

            self.after(0, self._handle_voice_input, text)
            # Wait for AI to finish speaking before we listen again (barge-in aside)
            time.sleep(1.2)
            while is_speaking() and not self._muted:
                time.sleep(0.15)

    def _handle_voice_input(self, text: str):
        """Decide if input is a command to execute or a conversational reply."""
        self._log(f"🗣 You: {text}")

        # Classify: command vs conversation using a quick Claude call
        threading.Thread(
            target=self._classify_and_respond, args=(text,), daemon=True
        ).start()

    def _classify_and_respond(self, text: str):
        """Background: classify speech then either run task or chat back."""
        try:
            gh = os.getenv("GITHUB_TOKEN", "")
            ak = os.getenv("ANTHROPIC_API_KEY", "")
            if not gh and (not ak or ak == "your_anthropic_key_here"):
                self.after(0, self._run_as_task, text)
                return

            # Build message content — include all attached screenshots if available
            user_content = []
            imgs = [f for f in self._attached_files if f.get("content_type") == "image"]
            for img_af in imgs:
                user_content.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": img_af.get("media_type", "image/png"),
                        "data": img_af["data"],
                    },
                })
            if imgs:
                self.after(0, self._clear_attachment)
            user_content.append({"type": "text", "text": text})

            # Add to memory
            conv_memory.add("user", text)

            # Build messages with history
            history = conv_memory.get_for_api()[:-1]  # all except last (just added)
            messages = history + [{"role": "user", "content": user_content}]

            reply = self._ai_chat(
                messages=messages,
                system=(
                    "You are a smart, friendly, and slightly sassy AI voice assistant named 'Hey Girl' "
                    "controlling a Windows PC. You can see the user's screen. "
                    "You have memory of the full conversation. "
                    "Decide the type of the user's message:\n"
                    "- If COMMAND (do something on the PC): reply with exactly: CMD: <the command>\n"
                    "- If SCREEN ANALYSIS REQUEST (e.g. 'what do you see', 'what's on my screen', "
                    "'analyze screen', 'what's happening', 'describe my screen', 'what's open'): "
                    "reply with exactly: SCREEN: <optional specific question to answer about the screen>\n"
                    "- If CONVERSATION (chat, question, opinion): reply naturally in 1-2 short sentences. "
                    "Be warm, witty, and helpful. Reference what you see on screen if relevant."
                ),
                max_tokens=400,
            )

            if reply.startswith("CMD:"):
                cmd = reply[4:].strip()
                conv_memory.add("assistant", f"Running command: {cmd}")
                self.after(0, self._run_as_task, cmd)
            elif reply.startswith("SCREEN:"):
                # AI wants a screen analysis
                screen_prompt = reply[7:].strip() or None
                conv_memory.add("assistant", "[Analyzing screen…]")
                self.after(0, self._analyze_screen, screen_prompt)
            else:
                conv_memory.add("assistant", reply)
                log_queue.put(f"🤖 Assistant: {reply}")
                speak(reply)
                self.after(0, self.footer_label.configure,
                           {"text": "🎤 Listening...", "text_color": "#66bb6a"})
        except Exception as e:
            log_queue.put(f"❌ Voice classify error: {e}")
            self.after(0, self._run_as_task, text)

    def _ai_chat(self, messages: list, system: str, max_tokens: int = 400) -> str:
        """
        Route AI chat to GitHub Models (free, Copilot subscription)
        or fall back to Anthropic Claude.
        Accepts messages in Anthropic format; auto-converts for OpenAI when using GitHub.
        """
        gh = os.getenv("GITHUB_TOKEN", "")
        ak = os.getenv("ANTHROPIC_API_KEY", "")

        if gh:
            # ── GitHub Models — free with Copilot subscription ──────────
            from openai import OpenAI as _OpenAI
            client = _OpenAI(base_url=GITHUB_API_URL, api_key=gh)
            oai_messages = [{"role": "system", "content": system}]
            for m in messages:
                c = m["content"]
                if isinstance(c, list):
                    oai_parts = []
                    for part in c:
                        if part["type"] == "text":
                            oai_parts.append({"type": "text", "text": part["text"]})
                        elif part["type"] == "image":
                            src = part["source"]
                            oai_parts.append({"type": "image_url", "image_url": {
                                "url": f"data:{src['media_type']};base64,{src['data']}"
                            }})
                    oai_messages.append({"role": m["role"], "content": oai_parts})
                else:
                    oai_messages.append({"role": m["role"], "content": c})
            resp = client.chat.completions.create(
                model=GITHUB_MODEL, messages=oai_messages, max_tokens=max_tokens
            )
            return resp.choices[0].message.content.strip()

        elif ak and ak != "your_anthropic_key_here":
            # ── Anthropic Claude fallback ───────────────────────────────
            client = anthropic.Anthropic(api_key=ak)
            resp = client.messages.create(
                model=CLAUDE_MODEL, max_tokens=max_tokens,
                system=system, messages=messages,
            )
            return resp.content[0].text.strip()

        else:
            raise ValueError("No AI key configured. Add a GitHub Token or Anthropic key in ⚙ API Keys.")

    def _run_as_task(self, text: str):
        cur = self.task_entry.get("1.0", "end-1c")
        if cur == self._entry_placeholder:
            self.task_entry.delete("1.0", "end")
            self.task_entry._textbox.configure(foreground="#e0e0e0")
        else:
            self.task_entry.delete("1.0", "end")
        self.task_entry.insert("1.0", text)
        self._run_task()

    def _run_task(self):
        raw = self.task_entry.get("1.0", "end-1c").strip()
        task = "" if raw == self._entry_placeholder else raw

        # If screenshots are attached, go straight to smart multi-screenshot analysis
        imgs = [f for f in self._attached_files if f.get("content_type") == "image"]
        if imgs:
            user_question = task  # may be empty — we'll infer from history
            self.task_entry.delete("1.0", "end")
            self.task_entry.insert("1.0", self._entry_placeholder)
            self.task_entry._textbox.configure(foreground="#555")
            n = len(imgs)
            self._log(f"🗣 You: {user_question or f'(analyzing {n} screenshot{chr(115) if n>1 else chr(32)}…)'.strip()}")
            af_list = imgs[:]
            self._attached_files = []
            self.after(0, self._clear_attachment)
            threading.Thread(target=self._screenshot_analyze_worker,
                             args=(af_list, user_question), daemon=True).start()
            return

        if not task:
            self._log("⚠ Please enter a task first.")
            return
        if self._running:
            self._log("⚠ Agent is already running. Stop it first.")
            return
        if not os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY") == "your_anthropic_key_here":
            self._log("❌ Anthropic API key not set. Click ⚙ API Keys to add it.")
            return

        # Clear the input box and restore placeholder
        self.task_entry.delete("1.0", "end")
        self.task_entry.insert("1.0", self._entry_placeholder)
        self.task_entry._textbox.configure(foreground="#555")

        self._running = True
        self.run_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.footer_label.configure(text="🔄 Agent running...", text_color="#4fc3f7")
        self._log(f"\n{'─'*50}\n▶ Starting: {task}\n{'─'*50}")

        # Redirect stdout to log
        sys.stdout = QueueWriter(log_queue)
        sys.stderr = QueueWriter(log_queue)

        self._agent_thread = threading.Thread(
            target=self._agent_worker, args=(task,), daemon=True
        )
        self._agent_thread.start()

    def _agent_worker(self, task: str):
        try:
            from main import run
            run(task)
        except Exception as e:
            log_queue.put(f"❌ Error: {e}")
        finally:
            sys.stdout = sys.__stdout__
            sys.stderr = sys.__stderr__
            self._running = False
            self.after(0, self._on_agent_done)

    def _on_agent_done(self):
        self.run_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        if self._muted:
            self.footer_label.configure(text="✅ Done — type your next command", text_color="#66bb6a")
        else:
            self.footer_label.configure(text="✅ Done — say 'Hey Girl' or type below", text_color="#66bb6a")
        self._log("✅ Task complete.\n")
        # Short done signal — don't ask a follow-up question that expects a reply
        speak("Done!")
        # Reset conversation mode so listener goes back to waiting silently for wake word
        self._in_conversation = False
        self._silence_count = 0

    def _stop_task(self):
        if self._running:
            self._log("⏹ Stop requested. The agent will halt after the current action.")
            # Hard stop — daemon thread will die when we clear the flag
            self._running = False
            self._on_agent_done()

    def _clear_log(self):
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")
        self.log_box._textbox.delete("1.0", "end")

    def _clear_memory(self):
        conv_memory.clear()
        self._log("🧠 Conversation memory cleared.")

    def _update_cost_display(self):
        today = cost_tracker.get_today_total()
        limit = cost_tracker.get_daily_limit()
        pct = (today / limit * 100) if limit > 0 else 0
        ratio = min(pct / 100.0, 1.0)

        # Progress bar colour: green → amber → red
        if pct < 70:
            bar_color = "#388e3c"   # green
            text_color = "#888"
        elif pct < 90:
            bar_color = "#f57c00"   # amber
            text_color = "#ffa726"
        else:
            bar_color = "#c62828"   # red
            text_color = "#ef5350"

        self.budget_progress.configure(progress_color=bar_color)
        self.budget_progress.set(ratio)
        self.budget_detail_label.configure(
            text=f"${today:.4f} / ${limit:.2f}  ({pct:.0f}%)",
            text_color=text_color,
        )

        # Footer small label
        self.cost_label.configure(
            text=f"💰 ${today:.4f} / ${limit:.2f}  ({pct:.0f}%)",
            text_color=text_color,
        )

        # ── Live recent-calls ticker ───────────────────────────────────────────
        SOURCE_ICON = {
            "whisper":    "🎙",
            "tts":        "🔊",
            "claude":     "🤖",
            "openai_cua": "🌐",
        }
        events = cost_tracker.get_events(4)
        if events:
            parts = []
            for e in reversed(events):
                icon = SOURCE_ICON.get(e["source"], "•")
                parts.append(f"{icon} {e['source']} {e['detail']}  +${e['cost']:.5f}  @{e['time']}")
            ticker = "    │    ".join(parts)
            # colour intensifies as cost grows
            ticker_color = "#4fc3f7" if pct < 70 else ("#ffa726" if pct < 90 else "#ef5350")
            self.live_calls_label.configure(text=ticker, text_color=ticker_color)
        else:
            self.live_calls_label.configure(text="No API calls yet today", text_color="#333")

        # ── Spoken warnings (once per session) ────────────────────────────────
        if pct >= 70 and not self._budget_warned_70:
            self._budget_warned_70 = True
            remaining = limit - today
            self._log(f"⚠ Budget at {pct:.0f}% — ${remaining:.4f} remaining today.")
            speak(f"Heads up — you've used {int(pct)} percent of your daily budget. "
                  f"About {remaining*100:.1f} cents left.")

        if pct >= 90 and not self._budget_warned_90:
            self._budget_warned_90 = True
            remaining = limit - today
            self._log(f"🚨 Budget at {pct:.0f}%! Only ${remaining:.4f} left — switching to free fallbacks soon.")
            speak("Warning — you're almost at your daily spending limit. "
                  "I'll switch to free voice recognition if you hit it.")

    def _poll_cost(self):
        """Refresh the cost display every second for a live feel."""
        self._update_cost_display()
        self.after(1000, self._poll_cost)

    # ── Settings window ───────────────────────────────────────────────────────

    def _open_settings(self):
        win = ctk.CTkToplevel(self)
        win.title("API Keys")
        win.geometry("560x360")
        win.resizable(False, False)
        win.grab_set()

        ctk.CTkLabel(win, text="API Keys", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(20, 2))
        ctk.CTkLabel(
            win,
            text="GitHub Token = free AI via your Copilot subscription. Anthropic/OpenAI are paid fallbacks.",
            text_color="#888", font=ctk.CTkFont(size=11),
        ).pack()

        frame = ctk.CTkFrame(win, fg_color="transparent")
        frame.pack(fill="x", padx=30, pady=12)
        frame.grid_columnconfigure(1, weight=1)

        # ── GitHub Token (free) ──────────────────────────────────────────
        ctk.CTkLabel(frame, text="🟢 GitHub Token:", anchor="w",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color="#66bb6a").grid(row=0, column=0, sticky="w", pady=(0, 2))
        gh_entry = ctk.CTkEntry(frame, width=330, show="*")
        gh_entry.grid(row=0, column=1, padx=(12, 0), pady=(0, 2))
        gh_val = os.getenv("GITHUB_TOKEN", "")
        if gh_val:
            gh_entry.insert(0, gh_val)
        ctk.CTkLabel(
            frame,
            text="↗ github.com/settings/tokens  → Generate new token (classic)  → tick read:user",
            text_color="#4fc3f7", font=ctk.CTkFont(size=10),
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, 10))

        # ── Anthropic ───────────────────────────────────────────────────
        ctk.CTkLabel(frame, text="Anthropic Key:", anchor="w",
                     text_color="#888").grid(row=2, column=0, sticky="w", pady=4)
        anthropic_entry = ctk.CTkEntry(frame, width=330, show="*")
        anthropic_entry.grid(row=2, column=1, padx=(12, 0))
        val = os.getenv("ANTHROPIC_API_KEY", "")
        if val and val != "your_anthropic_key_here":
            anthropic_entry.insert(0, val)

        # ── OpenAI ─────────────────────────────────────────────────────
        ctk.CTkLabel(frame, text="OpenAI Key:", anchor="w",
                     text_color="#888").grid(row=3, column=0, sticky="w", pady=4)
        openai_entry = ctk.CTkEntry(frame, width=330, show="*")
        openai_entry.grid(row=3, column=1, padx=(12, 0))
        val2 = os.getenv("OPENAI_API_KEY", "")
        if val2 and val2 != "your_openai_key_here":
            openai_entry.insert(0, val2)

        def save():
            gh  = gh_entry.get().strip()
            ak  = anthropic_entry.get().strip()
            ok  = openai_entry.get().strip()
            env_path = os.path.join(os.path.dirname(__file__), ".env")
            if gh:
                set_key(env_path, "GITHUB_TOKEN", gh)
                os.environ["GITHUB_TOKEN"] = gh
            if ak:
                set_key(env_path, "ANTHROPIC_API_KEY", ak)
                os.environ["ANTHROPIC_API_KEY"] = ak
            if ok:
                set_key(env_path, "OPENAI_API_KEY", ok)
                os.environ["OPENAI_API_KEY"] = ok
            self._check_api_keys()
            win.destroy()
            self._log("✅ API keys saved.")

        ctk.CTkButton(win, text="Save", width=120, command=save).pack(pady=10)

    # ── Helpers ───────────────────────────────────────────────────────────────


    def _open_voice_settings(self):
        win = ctk.CTkToplevel(self)
        win.title("Voice & Cost Settings")
        win.geometry("560x800")
        win.resizable(False, False)
        win.grab_set()

        ctk.CTkLabel(win, text="Voice & Cost Settings",
                     font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(18, 2))

        # ── Voice Presets ──────────────────────────────────────────────────────
        ctk.CTkLabel(win, text="🎙 Quick Voice Presets",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color="#f48fb1").pack(anchor="w", padx=28, pady=(6, 2))

        preset_outer = ctk.CTkFrame(win, fg_color="#1a1a2e", corner_radius=8)
        preset_outer.pack(fill="x", padx=20, pady=(0, 8))

        preset_row1 = ctk.CTkFrame(preset_outer, fg_color="transparent")
        preset_row1.pack(fill="x", padx=10, pady=(8, 4))

        selected_preset_var = ctk.StringVar(value="")

        def apply_preset(name: str):
            p = VOICE_PRESETS[name]
            voice_settings["openai_voice"] = p["voice"]
            voice_settings["voice_instructions"] = p["instructions"]
            # Update the dropdown to match
            match = next((k for k, v in OPENAI_VOICES.items() if v == p["voice"]), None)
            if match:
                voice_var.set(match)
            instr_box.configure(state="normal")
            instr_box.delete("1.0", "end")
            instr_box.insert("end", p["instructions"])
            instr_box.configure(state="normal")
            selected_preset_var.set(name)
            # Preview immediately
            _preview_openai(p["voice"], p["instructions"])

        def _preview_openai(voice_id: str, instructions: str = ""):
            """Play a quick sample by temporarily swapping voice settings and calling speak()."""
            api_key = os.getenv("OPENAI_API_KEY", "")
            if not api_key or api_key == "your_openai_key_here":
                messagebox.showerror(
                    "No OpenAI Key",
                    "Voice preview needs an OpenAI API key.\n\nClick ⚙ API Keys and add your OpenAI key.",
                    parent=win,
                )
                return
            # Temporarily swap voice settings, speak, then restore
            old_voice = voice_settings.get("openai_voice")
            old_instr = voice_settings.get("voice_instructions", "")
            voice_settings["openai_voice"] = voice_id
            voice_settings["voice_instructions"] = instructions
            speak("Hey girl! This is how I sound. Do you like my voice?")
            def _restore():
                import time; time.sleep(6)
                voice_settings["openai_voice"] = old_voice
                voice_settings["voice_instructions"] = old_instr
            threading.Thread(target=_restore, daemon=True).start()

        preset_colors = {
            "🇺🇸 Sweet American": ("#880e4f", "#ad1457"),
        }

        preset_names = list(VOICE_PRESETS.keys())
        for i, name in enumerate(preset_names):
            col = i % 3
            row_frame = preset_row1 if i < 3 else (
                preset_outer.winfo_children()[-1]
                if i == 3 else None
            )
            if i == 3:
                row_frame = ctk.CTkFrame(preset_outer, fg_color="transparent")
                row_frame.pack(fill="x", padx=10, pady=(0, 8))
            elif i > 3 and not (i == 3):
                row_frame = preset_outer.winfo_children()[-1]
            colors = preset_colors.get(name, ("#333", "#555"))
            ctk.CTkButton(
                row_frame, text=name, width=155, height=34,
                font=ctk.CTkFont(size=11, weight="bold"),
                fg_color=colors[0], hover_color=colors[1],
                command=lambda n=name: apply_preset(n),
            ).pack(side="left", padx=4)

        frame = ctk.CTkFrame(win, fg_color="transparent")
        frame.pack(fill="x", padx=28, pady=4)

        # OpenAI voice (only engine — Windows TTS removed)
        ctk.CTkLabel(frame, text="Voice:", anchor="w").grid(row=1, column=0, sticky="w", pady=6)
        voice_labels = list(OPENAI_VOICES.keys())
        current_voice_label = next((k for k, v in OPENAI_VOICES.items() if v == voice_settings["openai_voice"]), voice_labels[0])
        voice_var = ctk.StringVar(value=current_voice_label)
        voice_menu = ctk.CTkOptionMenu(frame, values=voice_labels, variable=voice_var, width=200)
        voice_menu.grid(row=1, column=1, padx=(12, 0))
        ctk.CTkButton(
            frame, text="▶ Try", width=52, height=28,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#880e4f", hover_color="#ad1457",
            command=lambda: _preview_openai(
                OPENAI_VOICES.get(voice_var.get(), "nova"),
                instr_box.get("1.0", "end").strip(),
            ),
        ).grid(row=1, column=2, padx=(8, 0))

        # Voice instructions (accent / style)
        ctk.CTkLabel(frame, text="Accent / Style:", anchor="w").grid(row=2, column=0, sticky="nw", pady=6)
        instr_box = ctk.CTkTextbox(frame, height=52, width=310, font=ctk.CTkFont(size=11), fg_color="#111")
        instr_box.insert("end", voice_settings.get("voice_instructions", ""))
        instr_box.grid(row=2, column=1, padx=(12, 0), pady=4)
        ctk.CTkLabel(frame, text="(gpt-4o-mini-tts — shapes accent & personality)",
                     text_color="#555", font=ctk.CTkFont(size=10)).grid(row=3, column=1, sticky="w", padx=(12, 0))

        # Microphone input selection
        ctk.CTkLabel(frame, text="Microphone:", anchor="w").grid(row=5, column=0, sticky="w", pady=6)
        input_devices = get_input_devices()  # [(index, name), ...]
        device_labels = ["System Default"] + [f"{idx}: {name}" for idx, name in input_devices]
        current_dev = voice_settings["microphone_device"]
        if current_dev is None:
            current_device_label = "System Default"
        else:
            current_device_label = next(
                (f"{idx}: {name}" for idx, name in input_devices if idx == current_dev),
                "System Default",
            )
        mic_var = ctk.StringVar(value=current_device_label)
        mic_menu = ctk.CTkOptionMenu(frame, values=device_labels, variable=mic_var, width=300,
                                     font=ctk.CTkFont(size=11))
        mic_menu.grid(row=5, column=1, padx=(12, 0), columnspan=2, sticky="w")

        # VAD sensitivity
        ctk.CTkLabel(frame, text="Mic Sensitivity:", anchor="w").grid(row=6, column=0, sticky="w", pady=6)
        vad_slider = ctk.CTkSlider(frame, from_=0.005, to=0.1, width=180)
        vad_slider.set(voice_settings["vad_threshold"])
        vad_slider.grid(row=6, column=1, padx=(12, 0))
        ctk.CTkLabel(frame, text="(lower = more sensitive)", text_color="#888",
                     font=ctk.CTkFont(size=10)).grid(row=7, column=1, sticky="w", padx=(12, 0))

        # ── Mic Test ──────────────────────────────────────────────────────────
        ctk.CTkLabel(frame, text="─" * 50, text_color="#333",
                     font=ctk.CTkFont(size=10)).grid(row=8, column=0, columnspan=3, sticky="ew", pady=(6, 0))
        ctk.CTkLabel(frame, text="🎤 Test Microphone",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color="#4fc3f7").grid(row=9, column=0, columnspan=3, sticky="w", pady=(2, 0))

        mic_test_row = ctk.CTkFrame(frame, fg_color="transparent")
        mic_test_row.grid(row=10, column=0, columnspan=3, sticky="ew", pady=(4, 0))

        mic_result_var = ctk.StringVar(value="Press button and speak — result appears here.")
        mic_result_lbl = ctk.CTkLabel(
            mic_test_row, textvariable=mic_result_var,
            wraplength=330, justify="left",
            font=ctk.CTkFont(size=11), text_color="#ccc",
            fg_color="#111", corner_radius=6,
            width=330, height=48,
        )
        mic_result_lbl.pack(side="left", padx=(0, 6))

        mic_level_var = ctk.StringVar(value="▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁")

        # stored recording for playback
        _last_recording = {"frames": None, "sr": 16000}

        def _play_back():
            frames = _last_recording["frames"]
            sr_val = _last_recording["sr"]
            if frames is None:
                return
            import io, wave
            try:
                import pygame
                buf = io.BytesIO()
                with wave.open(buf, "wb") as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(sr_val)
                    wf.writeframes(frames.tobytes())
                buf.seek(0)
                pygame.mixer.init(frequency=sr_val, size=-16, channels=1, buffer=512)
                sound = pygame.mixer.Sound(buf)
                mic_result_var.set("🔊 Playing back…")
                playback_btn.configure(state="disabled")
                def _after_play():
                    sound.play()
                    import time
                    dur = sound.get_length()
                    time.sleep(dur + 0.2)
                    win.after(0, lambda: mic_result_var.set("✅ Playback done."))
                    win.after(0, lambda: playback_btn.configure(state="normal"))
                threading.Thread(target=_after_play, daemon=True).start()
            except Exception as e:
                mic_result_var.set(f"❌ Playback error: {e}")

        def _run_mic_test():
            import io, wave, time
            import numpy as np
            import sounddevice as sd

            mic_result_var.set("🎙 Listening for 3 seconds…")
            mic_test_btn.configure(state="disabled", text="…")
            playback_btn.configure(state="disabled")

            def _record_and_transcribe():
                sr_val = 16000
                dur = 3
                device = voice_settings["microphone_device"]
                try:
                    frames = sd.rec(int(sr_val * dur), samplerate=sr_val,
                                    channels=1, dtype="int16", device=device)
                    # stream level updates while recording
                    for i in range(30):
                        time.sleep(0.1)
                        if frames is not None:
                            chunk = frames[:int(sr_val * (i + 1) / 10)]
                            if len(chunk):
                                rms = float(np.sqrt(np.mean(chunk.astype(np.float32) ** 2))) / 32768
                                bars = int(rms * 16 / 0.3)
                                bars = max(1, min(16, bars))
                                bar_str = "█" * bars + "▁" * (16 - bars)
                                mic_level_var.set(bar_str)
                    sd.wait()

                    # store for playback
                    _last_recording["frames"] = frames.copy()
                    _last_recording["sr"] = sr_val
                    win.after(0, lambda: playback_btn.configure(state="normal"))

                    # compute peak RMS
                    arr = frames.flatten().astype(np.float32) / 32768.0
                    peak = float(np.sqrt(np.mean(arr ** 2)))

                    if peak < 0.005:
                        win.after(0, lambda: mic_result_var.set("⚠️ Mic too quiet — check your microphone or sensitivity setting."))
                        win.after(0, lambda: mic_test_btn.configure(state="normal", text="🎤 Test Mic"))
                        win.after(0, lambda: mic_level_var.set("▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁"))
                        return

                    # Try Whisper transcription
                    api_key = os.getenv("OPENAI_API_KEY", "")
                    if api_key and api_key != "your_openai_key_here":
                        try:
                            from openai import OpenAI
                            buf = io.BytesIO()
                            with wave.open(buf, "wb") as wf:
                                wf.setnchannels(1)
                                wf.setsampwidth(2)
                                wf.setframerate(sr_val)
                                wf.writeframes(frames.tobytes())
                            buf.seek(0)
                            buf.name = "mic_test.wav"
                            client = OpenAI(api_key=api_key)
                            result = client.audio.transcriptions.create(
                                model="whisper-1", file=buf, language="en"
                            )
                            text = result.text.strip() or "(silence or unclear)"
                            win.after(0, lambda t=text: mic_result_var.set(f"✅ Heard: \"{t}\""))
                        except Exception as e:
                            win.after(0, lambda: mic_result_var.set(f"✅ Mic working! (Whisper error: {e})"))
                    else:
                        db = 20 * np.log10(peak + 1e-9)
                        win.after(0, lambda d=db: mic_result_var.set(
                            f"✅ Mic working! Peak level: {d:.1f} dB  (add OpenAI key for transcription)"))

                    win.after(0, lambda: mic_test_btn.configure(state="normal", text="🎤 Test Mic"))
                    win.after(0, lambda: mic_level_var.set("▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁"))

                except Exception as e:
                    win.after(0, lambda: mic_result_var.set(f"❌ Error: {e}"))
                    win.after(0, lambda: mic_test_btn.configure(state="normal", text="🎤 Test Mic"))

            threading.Thread(target=_record_and_transcribe, daemon=True).start()

        btn_col = ctk.CTkFrame(mic_test_row, fg_color="transparent")
        btn_col.pack(side="left")

        mic_test_btn = ctk.CTkButton(
            btn_col, text="🎤 Test Mic", width=100, height=34,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#0d3b2e", hover_color="#1b5e40",
            command=_run_mic_test,
        )
        mic_test_btn.pack(pady=(0, 4))

        playback_btn = ctk.CTkButton(
            btn_col, text="▶ Play Back", width=100, height=34,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#1a237e", hover_color="#283593",
            state="disabled",
            command=_play_back,
        )
        playback_btn.pack()

        mic_level_lbl = ctk.CTkLabel(
            frame, textvariable=mic_level_var,
            font=ctk.CTkFont(family="Courier New", size=11),
            text_color="#4fc3f7",
        )
        mic_level_lbl.grid(row=11, column=0, columnspan=3, sticky="w", padx=(2, 0), pady=(0, 4))

        # ── Cost controls ──────────────────────────────────────────────────────
        ctk.CTkLabel(frame, text="─" * 50, text_color="#333",
                     font=ctk.CTkFont(size=10)).grid(row=12, column=0, columnspan=3, sticky="ew", pady=(6, 0))
        ctk.CTkLabel(frame, text="Cost Controls", font=ctk.CTkFont(size=12, weight="bold"),
                     text_color="#4fc3f7").grid(row=13, column=0, columnspan=3, sticky="w")

        ctk.CTkLabel(frame, text="Wake Word:", anchor="w").grid(row=14, column=0, sticky="w", pady=6)
        wake_var = ctk.BooleanVar(value=self._wake_word_enabled)
        ctk.CTkSwitch(frame, text='Say "Hey Girl" to activate  (saves ~90% cost)',
                      variable=wake_var, font=ctk.CTkFont(size=11), text_color="#aaa",
                      ).grid(row=14, column=1, padx=(12, 0), sticky="w")

        ctk.CTkLabel(frame, text="Daily Limit ($):", anchor="w").grid(row=15, column=0, sticky="w", pady=6)
        limit_frame = ctk.CTkFrame(frame, fg_color="transparent")
        limit_frame.grid(row=15, column=1, padx=(12, 0), sticky="w")
        limit_slider = ctk.CTkSlider(limit_frame, from_=0.10, to=5.00, width=150)
        limit_slider.set(cost_tracker.get_daily_limit())
        limit_slider.pack(side="left")
        limit_val_label = ctk.CTkLabel(limit_frame, text=f"${cost_tracker.get_daily_limit():.2f}",
                                       font=ctk.CTkFont(size=12), text_color="#fff", width=50)
        limit_val_label.pack(side="left", padx=(8, 0))
        limit_slider.configure(command=lambda v: limit_val_label.configure(text=f"${float(v):.2f}"))

        today = cost_tracker.get_today_total()
        limit_now = cost_tracker.get_daily_limit()
        ctk.CTkLabel(frame, text="Today's Usage:", anchor="w").grid(row=16, column=0, sticky="w", pady=2)
        ctk.CTkLabel(
            frame,
            text=f"${today:.4f} of ${limit_now:.2f}  ({today/limit_now*100:.0f}%)" if limit_now else f"${today:.4f}",
            text_color="#66bb6a" if today < limit_now * 0.7 else "#ffa726",
            font=ctk.CTkFont(size=12),
        ).grid(row=16, column=1, padx=(12, 0), sticky="w")

        def reset_cost():
            cost_tracker.reset_today()
            self._log("💰 Daily cost counter reset.")
            self._update_cost_display()
            win.destroy()

        def save():
            voice_settings["openai_voice"] = OPENAI_VOICES.get(voice_var.get(), "nova")
            voice_settings["voice_instructions"] = instr_box.get("1.0", "end").strip()
            voice_settings["vad_threshold"] = float(vad_slider.get())
            self._wake_word_enabled = wake_var.get()
            cost_tracker.set_daily_limit(round(float(limit_slider.get()), 2))
            self._update_cost_display()
            # Save microphone device selection
            mic_sel = mic_var.get()
            if mic_sel == "System Default":
                voice_settings["microphone_device"] = None
            else:
                try:
                    voice_settings["microphone_device"] = int(mic_sel.split(":")[0])
                except (ValueError, IndexError):
                    voice_settings["microphone_device"] = None
            win.destroy()
            ww_str = "ON" if self._wake_word_enabled else "OFF"
            mic_str = mic_var.get()
            self._log(f"✅ Voice settings saved. Wake word: {ww_str}, Limit: ${cost_tracker.get_daily_limit():.2f}/day, Mic: {mic_str}")
            speak("Settings saved, girl.")

        def test_voice():
            _preview_openai(
                OPENAI_VOICES.get(voice_var.get(), "nova"),
                instr_box.get("1.0", "end").strip(),
            )

        btn_frame = ctk.CTkFrame(win, fg_color="transparent")
        btn_frame.pack(pady=10)
        ctk.CTkButton(btn_frame, text="🔊 Test Voice", width=120, fg_color="#333",
                      hover_color="#555", command=test_voice).pack(side="left", padx=6)
        ctk.CTkButton(btn_frame, text="Reset Today's Cost", width=140, fg_color="#4a1942",
                      hover_color="#6a1b9a", command=reset_cost).pack(side="left", padx=6)
        ctk.CTkButton(btn_frame, text="Save", width=100, command=save).pack(side="left", padx=6)

    def _check_api_keys(self):
        gh = os.getenv("GITHUB_TOKEN", "")
        ak = os.getenv("ANTHROPIC_API_KEY", "")
        ok = os.getenv("OPENAI_API_KEY", "")

        if gh:
            self.claude_status.configure(
                text="✅ GitHub Copilot — AI chat FREE", text_color="#66bb6a")
        elif ak and ak != "your_anthropic_key_here":
            self.claude_status.configure(
                text="✅ Anthropic Claude active", text_color="#66bb6a")
        else:
            self.claude_status.configure(
                text="❌ No AI key — click ⚙ API Keys", text_color="#ef5350")

        if ok and ok != "your_openai_key_here":
            self.openai_status.configure(
                text="✅ OpenAI: Whisper + TTS + Web", text_color="#66bb6a")
        else:
            self.openai_status.configure(
                text="ℹ No OpenAI key — free voice fallback active", text_color="#ffa726")

    def _log(self, text: str):
        t = self.log_box._textbox
        t.configure(state="normal")

        # Pick color tag based on content
        tl = text.lower()
        if any(x in text for x in ["❌", "Error", "error", "ERROR", "failed", "Failed"]):
            tag = "error"
        elif any(x in text for x in ["✅", "complete", "Complete", "Done", "saved"]):
            tag = "success"
        elif any(x in text for x in ["⚠", "warning", "Warning", "optional", "fallback"]):
            tag = "warning"
        elif text.startswith("🗣 You:"):
            tag = "user"
        elif text.startswith("🤖 Assistant:"):
            tag = "bot"
        elif any(x in text for x in ["-> ", "Action:", "action:", "mouse", "click", "type", "key", "scroll"]):
            tag = "action"
        elif "[Router]" in text:
            tag = "router"
        elif "[Memory]" in text:
            tag = "memory"
        elif "[OpenAI CUA]" in text:
            tag = "openai"
        elif "[Agent]" in text:
            tag = "agent"
        elif "─" in text or "═" in text:
            tag = "divider"
        elif "▶ Starting" in text:
            tag = "task"
        else:
            tag = "default"

        start = t.index("end-1c")
        t.insert("end", text + "\n")
        end = t.index("end-1c")
        t.tag_add(tag, start, end)
        t.see("end")
        t.configure(state="disabled")

    def _poll_log(self):
        """Poll the log queue and update the UI — runs every 100ms."""
        try:
            while True:
                msg = log_queue.get_nowait()
                self._log(msg)
        except queue.Empty:
            pass
        self.after(100, self._poll_log)


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Single-instance guard: if already running, focus the existing window and exit
    import ctypes as _ctypes
    _MUTEX_NAME = "Global\\HeyGirlSingleInstance"
    _mutex_handle = _ctypes.windll.kernel32.CreateMutexW(None, True, _MUTEX_NAME)
    if _ctypes.windll.kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
        _hwnd = _ctypes.windll.user32.FindWindowW(None, "Hey Girl")
        if _hwnd:
            _ctypes.windll.user32.ShowWindow(_hwnd, 9)       # SW_RESTORE (un-minimise)
            _ctypes.windll.user32.SetForegroundWindow(_hwnd)  # bring to front
        sys.exit(0)

    # Start web server in background so the app is also accessible via browser
    try:
        import server as _server
        _web_port = 5000
        threading.Thread(
            target=_server.run_server,
            kwargs={"port": _web_port},
            daemon=True,
            name="WebServer",
        ).start()
        print(f"[Hey Girl] Web UI → http://localhost:{_web_port}")
    except Exception as _e:
        print(f"[Hey Girl] Web server could not start: {_e}")

    app = App()
    app.mainloop()
