"""
MLEbotics Hub
=============
One desktop app for Hey Girl, Computer Use, and AutoFormFiller.
Packaged as a standalone .exe via PyInstaller.

Run with:  python hub.py
           (from D:\\MLEbotics\\MLEbotics-Projects\\)
"""

import os
import sys
import io
import math
import random
import contextlib
import threading
import webbrowser
import importlib.util
import tkinter as tk
from tkinter import scrolledtext, messagebox

# ── Paths (supports both normal Python and PyInstaller frozen bundle) ──────────
if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

HEY_GIRL_DIR     = os.path.join(BASE_DIR, "hey-girl")
COMPUTER_USE_DIR = os.path.join(BASE_DIR, "Computer-Use")
AUTO_FORM_DIR    = os.path.join(BASE_DIR, "AutoFormFiller")
BACKEND_DIR      = os.path.join(AUTO_FORM_DIR, "backend")

for _p in (HEY_GIRL_DIR, COMPUTER_USE_DIR, BACKEND_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# ── Global server / state handles ─────────────────────────────────────────────
_flask_server: dict    = {"ref": None}
_compuse_running: dict = {"v": False}

# ── Colour palette ─────────────────────────────────────────────────────────────
BG          = "#0d0d1a"   # near-black space
PANEL       = "#13132a"   # card background
SIDEBAR_BG  = "#09091a"   # deep sidebar
BORDER      = "#1e1e40"   # subtle border

NEON_PINK   = "#ff2d78"   # Hey Girl
NEON_PURPLE = "#9b30ff"   # Computer Use
NEON_CYAN   = "#00d4ff"   # AutoFormFiller
NEON_GREEN  = "#00ff88"   # success / active
NEON_AMBER  = "#ffb300"   # warning

ACCENT      = NEON_PINK
ACCENT_CU   = NEON_PURPLE
ACCENT_AF   = NEON_CYAN
SUCCESS     = NEON_GREEN
WARN        = NEON_AMBER

TEXT_FG   = "#f0f0ff"
USER_FG   = "#80e8ff"
BOT_FG    = "#ffd166"
ENTRY_BG  = "#0f0f2e"
MUTED     = "#55557a"

F_MAIN    = ("Segoe UI", 11)
F_BOLD    = ("Segoe UI", 11, "bold")
F_TITLE   = ("Segoe UI", 14, "bold")
F_HERO    = ("Segoe UI", 28, "bold")
F_SMALL   = ("Segoe UI", 9)
F_MONO    = ("Consolas", 10)


# ── Helpers ────────────────────────────────────────────────────────────────────
def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def lerp_color(c1, c2, t):
    r1, g1, b1 = hex_to_rgb(c1)
    r2, g2, b2 = hex_to_rgb(c2)
    r = int(r1 + (r2 - r1) * t)
    g = int(g1 + (g2 - g1) * t)
    b = int(b1 + (b2 - b1) * t)
    return f"#{r:02x}{g:02x}{b:02x}"

def hover_bind(widget, normal_bg, hover_bg, normal_fg=TEXT_FG, hover_fg="white"):
    widget.bind("<Enter>",  lambda e: widget.config(bg=hover_bg,  fg=hover_fg))
    widget.bind("<Leave>",  lambda e: widget.config(bg=normal_bg, fg=normal_fg))

def neon_frame(parent, color, padx=20, pady=14):
    """Card with a 2px neon-coloured left border."""
    outer = tk.Frame(parent, bg=color)
    inner = tk.Frame(outer, bg=PANEL, padx=padx, pady=pady)
    inner.pack(padx=(3, 0), pady=0, fill=tk.BOTH, expand=True)
    return outer, inner

def section_title(parent, text, color):
    tk.Label(parent, text=text, font=F_BOLD, bg=PANEL, fg=color).pack(anchor="w")

def muted_label(parent, text):
    tk.Label(parent, text=text, font=F_SMALL, bg=PANEL, fg=MUTED,
             justify=tk.LEFT, wraplength=700).pack(anchor="w", pady=(2, 8))

def accent_btn(parent, text, cmd, color, **kw):
    padx = kw.pop("padx", 14)
    pady = kw.pop("pady", 5)
    b = tk.Button(parent, text=text, command=cmd,
                  bg=color, fg="white", font=F_BOLD,
                  relief=tk.FLAT, padx=padx, pady=pady,
                  cursor="hand2", activebackground=lerp_color(color, "#ffffff", 0.25),
                  activeforeground="white", **kw)
    hover_bind(b, color, lerp_color(color, "#ffffff", 0.2), "white", "white")
    return b

def ghost_btn(parent, text, cmd, **kw):
    b = tk.Button(parent, text=text, command=cmd,
                  bg=BORDER, fg=TEXT_FG, font=F_MAIN,
                  relief=tk.FLAT, padx=12, pady=4,
                  cursor="hand2", activebackground="#2a2a50",
                  activeforeground="white", **kw)
    hover_bind(b, BORDER, "#2a2a50")
    return b


# ── Dynamic module loader ──────────────────────────────────────────────────────
def _load_module(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod  = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ── Stdout redirect for capturing print() into a widget ───────────────────────
class _WidgetWriter(io.TextIOBase):
    def __init__(self, callback):
        self._cb = callback
    def write(self, s):
        if s:
            self._cb(s)
        return len(s)
    def flush(self):
        pass


# =============================================================================
# HOME PANEL  (animated starfield + hero section)
# =============================================================================
def build_home(parent: tk.Frame, root: tk.Tk) -> tk.Frame:
    f = tk.Frame(parent, bg=BG)

    # ── Animated canvas (starfield + glowing orbs) ────────────────────────────
    canvas = tk.Canvas(f, bg=BG, highlightthickness=0, height=380)
    canvas.pack(fill=tk.X)

    stars = []
    for _ in range(120):
        x = random.randint(0, 1100)
        y = random.randint(0, 380)
        r = random.choice([1, 1, 1, 2])
        speed = random.uniform(0.2, 0.8)
        brightness = random.choice(["#ffffff", "#aaaaff", "#ff88cc", "#88ffee"])
        oval = canvas.create_oval(x-r, y-r, x+r, y+r, fill=brightness, outline="")
        stars.append({"oval": oval, "x": x, "y": y, "r": r, "speed": speed})

    # Glowing orbs
    orb_data = [
        {"x": 200, "y": 150, "r": 70, "color": NEON_PINK,   "phase": 0.0},
        {"x": 600, "y": 100, "r": 55, "color": NEON_PURPLE, "phase": 1.0},
        {"x": 950, "y": 200, "r": 65, "color": NEON_CYAN,   "phase": 2.0},
    ]
    orb_items = []
    for o in orb_data:
        x, y, r, c = o["x"], o["y"], o["r"], o["color"]
        item = canvas.create_oval(x-r, y-r, x+r, y+r,
                                   fill=lerp_color(c, BG, 0.75), outline=c, width=2)
        orb_items.append(item)

    # Hero text on canvas
    canvas.create_text(550, 150, text="⚡ MLEbotics Hub",
                       font=("Segoe UI", 36, "bold"), fill=TEXT_FG, anchor="center")
    canvas.create_text(550, 200, text="Your all-in-one AI desktop toolkit",
                       font=("Segoe UI", 13), fill=MUTED, anchor="center")

    # Sub-badges
    badge_colors = [NEON_PINK, NEON_PURPLE, NEON_CYAN]
    badge_labels = ["🎙 Hey Girl", "🖥 Computer Use", "📝 AutoFormFiller"]
    for i, (label, color) in enumerate(zip(badge_labels, badge_colors)):
        bx = 330 + i * 220
        canvas.create_rectangle(bx-80, 248, bx+80, 278,
                                  fill=lerp_color(color, BG, 0.82), outline=color, width=1)
        canvas.create_text(bx, 263, text=label,
                            font=("Segoe UI", 10, "bold"), fill=color, anchor="center")

    _anim_running = {"v": True}
    tick = {"n": 0}

    def animate():
        if not _anim_running["v"]:
            return
        tick["n"] += 1
        t = tick["n"]

        # Drift stars left, wrap
        for s in stars:
            s["x"] -= s["speed"]
            if s["x"] < 0:
                s["x"] = 1100
                s["y"] = random.randint(0, 380)
            r = s["r"]
            canvas.coords(s["oval"], s["x"]-r, s["y"]-r, s["x"]+r, s["y"]+r)

        # Pulse orbs
        for i, (item, odata) in enumerate(zip(orb_items, orb_data)):
            phase = t * 0.04 + odata["phase"]
            alpha = 0.65 + 0.25 * math.sin(phase)
            r = odata["r"] + 6 * math.sin(phase)
            x, y = odata["x"], odata["y"]
            fill = lerp_color(odata["color"], BG, 1 - alpha * 0.35)
            canvas.coords(item, x-r, y-r, x+r, y+r)
            canvas.itemconfig(item, fill=fill)

        root.after(40, animate)

    animate()
    f.bind("<Destroy>", lambda e: _anim_running.update({"v": False}))

    # ── Feature cards ─────────────────────────────────────────────────────────
    cards_frame = tk.Frame(f, bg=BG)
    cards_frame.pack(pady=(0, 20))

    card_data = [
        ("🎙️", "Hey Girl",
         "Voice AI · Chat · Web Search\nWake word · Desktop commands",
         NEON_PINK),
        ("🖥️", "Computer Use",
         "AI sees your screen · Clicks\nTypes · Automates anything",
         NEON_PURPLE),
        ("📝", "AutoFormFiller",
         "AI fills web forms instantly\nChrome extension included",
         NEON_CYAN),
    ]

    for icon, title, desc, color in card_data:
        # Outer glow border
        glow = tk.Frame(cards_frame, bg=color, padx=2, pady=2)
        glow.pack(side=tk.LEFT, padx=16)
        inner = tk.Frame(glow, bg=PANEL, padx=26, pady=20)
        inner.pack()

        tk.Label(inner, text=icon, font=("Segoe UI", 32),
                 bg=PANEL, fg=color).pack()
        tk.Label(inner, text=title, font=("Segoe UI", 12, "bold"),
                 bg=PANEL, fg=TEXT_FG).pack(pady=(6, 2))
        tk.Label(inner, text=desc, font=F_SMALL,
                 bg=PANEL, fg=MUTED, justify=tk.CENTER).pack()

    tk.Label(f, text="← Select a tool from the sidebar",
             font=F_SMALL, bg=BG, fg=MUTED).pack(pady=(4, 16))

    return f


# =============================================================================
# HEY GIRL PANEL
# =============================================================================
def build_heygirl(parent: tk.Frame, root: tk.Tk) -> tk.Frame:
    f = tk.Frame(parent, bg=BG)

    try:
        from agent import speak, listen, web_search, start_wake_listener, stop_wake_listener
        from main import run as hg_run
        from memory import add_to_history, get_conversation_history, clear as clear_memory
        imports_ok = True
    except ImportError as e:
        imports_ok = False
        err_msg = str(e)

    if not imports_ok:
        tk.Label(f, text="⚠  Hey Girl dependencies not installed",
                 font=F_BOLD, bg=BG, fg=WARN).pack(pady=40)
        tk.Label(f,
                 text=f"Error: {err_msg}\n\nFix:\n  cd hey-girl\n  pip install -r requirements.txt",
                 font=F_MONO, bg=BG, fg=TEXT_FG, justify=tk.LEFT).pack(padx=30)
        return f

    # ── Header strip ──────────────────────────────────────────────────────────
    hdr = tk.Frame(f, bg=NEON_PINK, pady=1)
    hdr.pack(fill=tk.X)
    inner_hdr = tk.Frame(hdr, bg=lerp_color(NEON_PINK, BG, 0.82), pady=8)
    inner_hdr.pack(fill=tk.X, padx=1)
    tk.Label(inner_hdr, text="🎙️  Hey Girl  —  AI Voice Assistant",
             font=F_TITLE, bg=lerp_color(NEON_PINK, BG, 0.82),
             fg=NEON_PINK).pack(side=tk.LEFT, padx=16)

    status_var = tk.StringVar(value="● Ready")
    status_lbl = tk.Label(f, textvariable=status_var, bg=PANEL, fg=NEON_GREEN,
                           font=("Segoe UI", 9, "bold"), anchor="w", padx=12)
    status_lbl.pack(fill=tk.X)

    # Chat area
    chat_area = scrolledtext.ScrolledText(
        f, wrap=tk.WORD, font=F_MAIN,
        bg="#0a0a1e", fg=TEXT_FG, insertbackground=TEXT_FG,
        relief=tk.FLAT, bd=0, padx=12, pady=10, state=tk.DISABLED,
        selectbackground=NEON_PINK
    )
    chat_area.pack(fill=tk.BOTH, expand=True, padx=10, pady=(8, 4))
    chat_area.tag_config("user",   foreground=USER_FG,   font=F_BOLD)
    chat_area.tag_config("bot",    foreground=BOT_FG,    font=F_MAIN)
    chat_area.tag_config("system", foreground=NEON_GREEN, font=F_SMALL)

    def append(sender, msg, tag="bot"):
        chat_area.configure(state=tk.NORMAL)
        if sender:
            chat_area.insert(tk.END, f"\n{sender}: ", tag)
        chat_area.insert(tk.END, f"{msg}\n", tag)
        chat_area.configure(state=tk.DISABLED)
        chat_area.see(tk.END)

    append(None, "Hey Girl is online. Type or speak your command!", "system")

    # Input row
    input_frame = tk.Frame(f, bg=BG, pady=6)
    input_frame.pack(fill=tk.X, padx=10)

    # Neon border around entry
    entry_border = tk.Frame(input_frame, bg=NEON_PINK, padx=1, pady=1)
    entry_border.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
    entry = tk.Entry(entry_border, font=F_MAIN, bg=ENTRY_BG, fg=TEXT_FG,
                     insertbackground=NEON_PINK, relief=tk.FLAT, bd=6)
    entry.pack(fill=tk.X, ipady=5)

    btn_row = tk.Frame(f, bg=BG, pady=4)
    btn_row.pack(fill=tk.X, padx=10, pady=(0, 8))

    voice_active = {"v": False}
    wake_active  = {"v": False}

    def _btn(par, text, cmd, color=NEON_PINK):
        b = tk.Button(par, text=text, command=cmd,
                      bg=color, fg="white", font=F_MAIN,
                      relief=tk.FLAT, padx=12, pady=4, cursor="hand2",
                      activebackground=lerp_color(color, "#ffffff", 0.2),
                      activeforeground="white")
        hover_bind(b, color, lerp_color(color, "#ffffff", 0.18), "white", "white")
        return b

    def run_task(task):
        status_var.set("⏳ Processing…")
        try:
            add_to_history("user", task)
            result = hg_run(task, history=get_conversation_history())
            add_to_history("assistant", result or "")
            out = result or "Task complete."
            root.after(0, lambda: append("Hey Girl", out, "bot"))
            root.after(0, lambda: speak(out))
        except Exception as ex:
            root.after(0, lambda: append("Error", str(ex), "system"))
        finally:
            root.after(0, lambda: status_var.set("● Ready"))

    def send(event=None):
        task = entry.get().strip()
        if not task:
            return
        entry.delete(0, tk.END)
        append("You", task, "user")
        threading.Thread(target=run_task, args=(task,), daemon=True).start()

    entry.bind("<Return>", send)
    _btn(btn_row, "Send", send).pack(side=tk.LEFT, padx=(0, 6))

    def toggle_voice():
        if not voice_active["v"]:
            voice_active["v"] = True
            vbtn.config(text="🎙 Stop", bg=SUCCESS)
            status_var.set("Listening…")
            def _listen():
                result = listen(timeout=8, phrase_limit=15)
                voice_active["v"] = False
                root.after(0, lambda: vbtn.config(text="🎙 Voice", bg="#33334e"))
                if result:
                    root.after(0, lambda: entry.insert(0, result))
                root.after(0, lambda: status_var.set("Ready"))
            threading.Thread(target=_listen, daemon=True).start()
        else:
            voice_active["v"] = False
            vbtn.config(text="🎙 Voice", bg="#33334e")
            status_var.set("Ready")

    vbtn = _btn(btn_row, "🎙 Voice", toggle_voice, "#33334e")
    vbtn.pack(side=tk.LEFT, padx=(0, 6))

    def toggle_wake():
        if not wake_active["v"]:
            wake_active["v"] = True
            wbtn.config(text="👂 Listening…", bg=WARN)
            status_var.set("Always-on: say 'hey girl' to activate")
            def _cb(cmd):
                root.after(0, lambda: append("You (voice)", cmd, "user"))
                threading.Thread(target=run_task, args=(cmd,), daemon=True).start()
            start_wake_listener(_cb)
        else:
            wake_active["v"] = False
            stop_wake_listener()
            wbtn.config(text="👂 Wake Word", bg="#33334e")
            status_var.set("● Ready")

    wbtn = _btn(btn_row, "👂 Wake Word", toggle_wake, "#33334e")
    wbtn.pack(side=tk.LEFT, padx=(0, 6))

    def do_search():
        q = entry.get().strip()
        if not q:
            return
        entry.delete(0, tk.END)
        append("You", f"Search: {q}", "user")
        def _s():
            status_var.set("🔍 Searching…")
            r = web_search(q)
            root.after(0, lambda: append("Hey Girl", r, "bot"))
            root.after(0, lambda: speak(r))
            root.after(0, lambda: status_var.set("● Ready"))
        threading.Thread(target=_s, daemon=True).start()

    _btn(btn_row, "🔍 Search", do_search, "#33334e").pack(side=tk.LEFT, padx=(0, 6))

    def clear_chat():
        chat_area.configure(state=tk.NORMAL)
        chat_area.delete("1.0", tk.END)
        chat_area.configure(state=tk.DISABLED)
        clear_memory()
        append(None, "Chat cleared.", "system")

    _btn(btn_row, "🗑 Clear", clear_chat, "#33334e").pack(side=tk.RIGHT)

    return f


# =============================================================================
# COMPUTER USE PANEL
# =============================================================================
def build_compuse(parent: tk.Frame, root: tk.Tk) -> tk.Frame:
    f = tk.Frame(parent, bg=BG)

    hdr = tk.Frame(f, bg=NEON_PURPLE, pady=1)
    hdr.pack(fill=tk.X)
    inner_hdr = tk.Frame(hdr, bg=lerp_color(NEON_PURPLE, BG, 0.82), pady=8)
    inner_hdr.pack(fill=tk.X, padx=1)
    tk.Label(inner_hdr, text="🖥️  Computer Use  —  AI Desktop Agent",
             font=F_TITLE, bg=lerp_color(NEON_PURPLE, BG, 0.82),
             fg=NEON_PURPLE).pack(side=tk.LEFT, padx=16)

    # Safety notice
    notice = tk.Frame(f, bg=lerp_color("#ff0000", BG, 0.88), pady=8)
    notice.pack(fill=tk.X, padx=10, pady=(8, 0))
    tk.Label(notice,
             text="⚠  Move mouse to TOP-LEFT corner at any time to immediately abort the agent.",
             font=("Segoe UI", 9, "bold"),
             bg=lerp_color("#ff0000", BG, 0.88), fg="#ff6666").pack(padx=12)

    # Goal input
    goal_frame = tk.Frame(f, bg=BG, pady=10)
    goal_frame.pack(fill=tk.X, padx=10)
    tk.Label(goal_frame, text="Goal:", font=F_BOLD, bg=BG, fg=NEON_PURPLE).pack(side=tk.LEFT, padx=(0, 8))
    goal_border = tk.Frame(goal_frame, bg=NEON_PURPLE, padx=1, pady=1)
    goal_border.pack(side=tk.LEFT, fill=tk.X, expand=True)
    goal_entry = tk.Entry(goal_border, font=F_MAIN, bg=ENTRY_BG, fg=TEXT_FG,
                          insertbackground=NEON_PURPLE, relief=tk.FLAT, bd=6)
    goal_entry.pack(fill=tk.X, ipady=5)

    # Control bar
    ctrl = tk.Frame(f, bg=BG, pady=4)
    ctrl.pack(fill=tk.X, padx=10)

    status_var = tk.StringVar(value="⚫  Idle")
    tk.Label(ctrl, textvariable=status_var, bg=BG, fg=NEON_PURPLE,
             font=("Segoe UI", 9, "bold")).pack(side=tk.RIGHT, padx=8)

    # Live log
    log = scrolledtext.ScrolledText(
        f, wrap=tk.WORD, font=F_MONO,
        bg="#08081a", fg=NEON_GREEN,
        relief=tk.FLAT, bd=0, padx=12, pady=10, state=tk.DISABLED,
        selectbackground=NEON_PURPLE
    )
    log.pack(fill=tk.BOTH, expand=True, padx=10, pady=(4, 10))

    def log_write(text):
        log.configure(state=tk.NORMAL)
        log.insert(tk.END, text)
        log.configure(state=tk.DISABLED)
        log.see(tk.END)

    def run_agent():
        goal = goal_entry.get().strip()
        if not goal:
            messagebox.showwarning("No Goal", "Please enter a goal for the agent.")
            return
        if _compuse_running["v"]:
            messagebox.showinfo("Running", "Agent is already running. Stop it first (move mouse to top-left).")
            return

        log.configure(state=tk.NORMAL)
        log.delete("1.0", tk.END)
        log.configure(state=tk.DISABLED)
        log_write(f"▶ Starting agent\n  Goal: {goal}\n{'─'*50}\n")
        status_var.set("Running…")
        run_btn.config(text="⏹ Running…", bg="#cc3333", state=tk.DISABLED)
        _compuse_running["v"] = True

        def _run():
            try:
                cu_mod = _load_module(
                    "cu_main",
                    os.path.join(COMPUTER_USE_DIR, "main.py")
                )
                writer = _WidgetWriter(lambda t: root.after(0, lambda s=t: log_write(s)))
                with contextlib.redirect_stdout(writer):
                    cu_mod.run(goal, skip_confirm=True)
                root.after(0, lambda: status_var.set("Done ✓"))
            except Exception as ex:
                root.after(0, lambda: log_write(f"\n[ERROR] {ex}\n"))
                root.after(0, lambda: status_var.set("Error"))
            finally:
                _compuse_running["v"] = False
                root.after(0, lambda: run_btn.config(
                    text="▶ Run Agent", bg=ACCENT_CU, state=tk.NORMAL, command=run_agent))

        threading.Thread(target=_run, daemon=True).start()

    run_btn = accent_btn(ctrl, "▶ Run Agent", run_agent, NEON_PURPLE, pady=5)
    run_btn.pack(side=tk.LEFT)

    return f


# =============================================================================
# AUTOFORMFILLER PANEL
# =============================================================================
def build_autoform(parent: tk.Frame, root: tk.Tk) -> tk.Frame:
    f = tk.Frame(parent, bg=BG)

    hdr = tk.Frame(f, bg=NEON_CYAN, pady=1)
    hdr.pack(fill=tk.X)
    inner_hdr = tk.Frame(hdr, bg=lerp_color(NEON_CYAN, BG, 0.82), pady=8)
    inner_hdr.pack(fill=tk.X, padx=1)
    tk.Label(inner_hdr, text="📝  AutoFormFiller  —  Smart Form Filler",
             font=F_TITLE, bg=lerp_color(NEON_CYAN, BG, 0.82),
             fg=NEON_CYAN).pack(side=tk.LEFT, padx=16)

    # Backend server section
    srv_outer, srv_frame = neon_frame(f, NEON_CYAN)
    srv_outer.pack(fill=tk.X, padx=10, pady=(12, 6))

    section_title(srv_frame, "Local Backend Server", NEON_CYAN)
    muted_label(srv_frame,
        "The Chrome extension communicates with this server to fill forms using AI.")

    srv_status_var = tk.StringVar(value="⚫  Server stopped")
    srv_status_lbl = tk.Label(srv_frame, textvariable=srv_status_var,
                               font=("Segoe UI", 10, "bold"), bg=PANEL, fg=NEON_AMBER)
    srv_status_lbl.pack(anchor="w", pady=(0, 8))

    srv_log = scrolledtext.ScrolledText(
        srv_frame, wrap=tk.WORD, font=F_MONO,
        bg="#08081a", fg=NEON_GREEN,
        relief=tk.FLAT, bd=0, padx=8, pady=6, height=6, state=tk.DISABLED
    )
    srv_log.pack(fill=tk.X, pady=(0, 10))

    def srv_log_write(text):
        srv_log.configure(state=tk.NORMAL)
        srv_log.insert(tk.END, text)
        srv_log.configure(state=tk.DISABLED)
        srv_log.see(tk.END)

    def start_server():
        if _flask_server["ref"] is not None:
            return
        srv_log_write("▶ Starting Flask server on http://localhost:5000 …\n")
        srv_status_var.set("🟡  Starting…")
        srv_status_lbl.config(fg=WARN)
        srv_btn.config(text="⏹ Stop Server", bg="#cc3333", command=stop_server)

        def _run():
            try:
                from werkzeug.serving import make_server
                af_mod = _load_module(
                    "af_app",
                    os.path.join(BACKEND_DIR, "app.py")
                )
                server = make_server("127.0.0.1", 5000, af_mod.app)
                _flask_server["ref"] = server
                root.after(0, lambda: srv_status_var.set("🟢  Running  →  http://localhost:5000"))
                root.after(0, lambda: srv_status_lbl.config(fg=NEON_GREEN))
                root.after(0, lambda: srv_log_write("Server started. Open Chrome and use the extension.\n"))
                server.serve_forever()
            except OSError as ex:
                if "address already in use" in str(ex).lower() or "10048" in str(ex):
                    root.after(0, lambda: srv_log_write("[INFO] Port 5000 already in use — server may already be running.\n"))
                    root.after(0, lambda: srv_status_var.set("🟢  Running  →  http://localhost:5000"))
                    root.after(0, lambda: srv_status_lbl.config(fg=NEON_GREEN))
                else:
                    root.after(0, lambda: srv_log_write(f"[ERROR] {ex}\n"))
                    root.after(0, lambda: srv_status_var.set("⚫  Server stopped"))
                    root.after(0, lambda: srv_status_lbl.config(fg=WARN))
                    root.after(0, lambda: srv_btn.config(
                        text="▶ Start Server", bg=SUCCESS, command=start_server))
            except Exception as ex:
                root.after(0, lambda: srv_log_write(f"[ERROR] {ex}\n"))
                _flask_server["ref"] = None
                root.after(0, lambda: srv_status_var.set("⚫  Server stopped"))
                root.after(0, lambda: srv_status_lbl.config(fg=WARN))
                root.after(0, lambda: srv_btn.config(
                    text="▶ Start Server", bg=SUCCESS, command=start_server))

        threading.Thread(target=_run, daemon=True).start()

    def stop_server():
        srv = _flask_server["ref"]
        if srv:
            srv.shutdown()
            _flask_server["ref"] = None
        srv_log_write("[Stopped by user]\n")
        srv_status_var.set("⚫  Server stopped")
        srv_status_lbl.config(fg=WARN)
        srv_btn.config(text="▶ Start Server", bg=SUCCESS, command=start_server)

    srv_btn = accent_btn(srv_frame, "▶ Start Server", start_server, NEON_GREEN)
    srv_btn.pack(anchor="w")

    # Chrome Extension section
    ext_outer, ext_frame = neon_frame(f, NEON_CYAN)
    ext_outer.pack(fill=tk.X, padx=10, pady=6)

    section_title(ext_frame, "Chrome Extension", NEON_CYAN)
    muted_label(ext_frame,
        "Install the extension in Chrome to auto-fill forms on any website.")

    steps = [
        "1.   Click 'Open Extension Folder' below",
        "2.   Open Chrome → navigate to  chrome://extensions",
        "3.   Enable 'Developer mode' (toggle, top-right corner)",
        "4.   Click 'Load unpacked' → select the extension/ folder",
        "5.   The AutoFormFiller icon will appear in your Chrome toolbar",
        "6.   Make sure the backend server above is running before using it",
    ]
    for step in steps:
        tk.Label(ext_frame, text=step, font=F_SMALL, bg=PANEL, fg=TEXT_FG, anchor="w").pack(fill=tk.X, pady=1)

    btn_row = tk.Frame(ext_frame, bg=PANEL, pady=10)
    btn_row.pack(anchor="w")

    def open_ext_folder():
        ext_path = os.path.join(AUTO_FORM_DIR, "extension")
        if os.path.exists(ext_path):
            os.startfile(ext_path)
        else:
            messagebox.showerror("Not Found", f"Extension folder not found:\n{ext_path}")

    accent_btn(btn_row, "📁 Open Extension Folder", open_ext_folder, NEON_CYAN).pack(side=tk.LEFT, padx=(0, 8))
    ghost_btn(btn_row, "🌐 chrome://extensions",
              lambda: webbrowser.open("chrome://extensions")).pack(side=tk.LEFT)

    return f


# =============================================================================
# SETTINGS PANEL
# =============================================================================
def build_settings(parent: tk.Frame) -> tk.Frame:
    f = tk.Frame(parent, bg=BG)

    hdr = tk.Frame(f, bg="#6655cc", pady=1)
    hdr.pack(fill=tk.X)
    inner_hdr = tk.Frame(hdr, bg=lerp_color("#6655cc", BG, 0.82), pady=8)
    inner_hdr.pack(fill=tk.X, padx=1)
    tk.Label(inner_hdr, text="⚙️  Settings  —  API Keys & Config",
             font=F_TITLE, bg=lerp_color("#6655cc", BG, 0.82),
             fg="#aa99ff").pack(side=tk.LEFT, padx=16)

    def make_section(title, env_path, keys_needed, color):
        outer, sec = neon_frame(f, color)
        outer.pack(fill=tk.X, padx=10, pady=(10, 0))
        section_title(sec, title, color)
        tk.Label(sec, text=f"Keys: {keys_needed}",
                 font=F_SMALL, bg=PANEL, fg=MUTED).pack(anchor="w", pady=(2, 4))
        tk.Label(sec, text=env_path, font=F_MONO, bg=PANEL, fg="#9988cc").pack(anchor="w", pady=(0, 6))

        exists = os.path.exists(env_path)
        tk.Label(sec,
                 text="✅  .env file found" if exists
                 else "❌  .env not found — click to create from template",
                 font=("Segoe UI", 9, "bold"), bg=PANEL,
                 fg=NEON_GREEN if exists else NEON_AMBER).pack(anchor="w", pady=(0, 8))

        def open_env():
            if not os.path.exists(env_path):
                ex = env_path + ".example"
                if os.path.exists(ex):
                    import shutil
                    shutil.copy(ex, env_path)
                else:
                    with open(env_path, "w") as fh:
                        fh.write(f"# {title} API keys\n")
            os.startfile(env_path)

        accent_btn(sec, "📝 Open .env", open_env, color).pack(anchor="w")

    make_section("🎙️  Hey Girl",       os.path.join(HEY_GIRL_DIR, ".env"),
                 "OPENAI_API_KEY", NEON_PINK)
    make_section("🖥️  Computer Use",   os.path.join(COMPUTER_USE_DIR, ".env"),
                 "ANTHROPIC_API_KEY", NEON_PURPLE)
    make_section("📝  AutoFormFiller", os.path.join(BACKEND_DIR, ".env"),
                 "ANTHROPIC_API_KEY, GEMINI_API_KEY, OPENAI_API_KEY", NEON_CYAN)

    return f


# =============================================================================
# MAIN
# =============================================================================
def main():
    root = tk.Tk()
    root.title("MLEbotics Hub")
    root.geometry("1100x720")
    root.configure(bg=BG)
    root.resizable(True, True)

    # ── Top bar with gradient stripe ──────────────────────────────────────────
    topbar = tk.Frame(root, bg=BG, pady=0, height=46)
    topbar.pack(fill=tk.X)
    topbar.pack_propagate(False)

    topbar_canvas = tk.Canvas(topbar, height=46, highlightthickness=0, bg=BG)
    topbar_canvas.pack(fill=tk.X)

    def draw_topbar(event=None):
        w = topbar_canvas.winfo_width() or 1100
        topbar_canvas.delete("all")
        steps = 60
        seg = w / steps
        colors_gradient = [
            (0,   NEON_PINK),
            (0.45, NEON_PURPLE),
            (1.0,  NEON_CYAN),
        ]
        for i in range(steps):
            t = i / (steps - 1)
            # find segment
            c1, c2, local_t = NEON_PINK, NEON_PURPLE, t
            for j in range(len(colors_gradient) - 1):
                t0, col0 = colors_gradient[j]
                t1, col1 = colors_gradient[j+1]
                if t0 <= t <= t1:
                    local_t = (t - t0) / (t1 - t0)
                    c1, c2 = col0, col1
                    break
            fill = lerp_color(c1, c2, local_t)
            topbar_canvas.create_rectangle(
                i * seg, 0, (i+1) * seg + 1, 46, fill=fill, outline="")
        topbar_canvas.create_text(16, 23, text="⚡ MLEbotics Hub",
                                   font=("Segoe UI Emoji", 14, "bold"), fill="white", anchor="w")
        topbar_canvas.create_text(200, 23,
                                   text="Hey Girl  ·  Computer Use  ·  AutoFormFiller",
                                   font=F_SMALL, fill="#ffffff88", anchor="w")

    topbar_canvas.bind("<Configure>", lambda e: draw_topbar())
    root.after(100, draw_topbar)

    # Layout
    body = tk.Frame(root, bg=BG)
    body.pack(fill=tk.BOTH, expand=True)

    sidebar = tk.Frame(body, bg=SIDEBAR_BG, width=210)
    sidebar.pack(side=tk.LEFT, fill=tk.Y)
    sidebar.pack_propagate(False)

    content = tk.Frame(body, bg=BG)
    content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    # Build all panels
    panels = {
        "home":     build_home(content, root),
        "heygirl":  build_heygirl(content, root),
        "compuse":  build_compuse(content, root),
        "autoform": build_autoform(content, root),
        "settings": build_settings(content),
    }

    def show(name):
        for p in panels.values():
            p.pack_forget()
        panels[name].pack(fill=tk.BOTH, expand=True)

    # ── Sidebar logo ──────────────────────────────────────────────────────────
    logo_frame = tk.Frame(sidebar, bg=SIDEBAR_BG, pady=18)
    logo_frame.pack(fill=tk.X)
    tk.Label(logo_frame, text="⚡", font=("Segoe UI Emoji", 22),
             bg=SIDEBAR_BG, fg=NEON_PINK).pack()
    tk.Label(logo_frame, text="MLEbotics", font=("Segoe UI", 11, "bold"),
             bg=SIDEBAR_BG, fg=TEXT_FG).pack()
    tk.Label(logo_frame, text="Hub", font=("Segoe UI", 9),
             bg=SIDEBAR_BG, fg=MUTED).pack()

    tk.Frame(sidebar, bg=BORDER, height=1).pack(fill=tk.X, padx=12, pady=(0, 8))

    # ── Nav items ─────────────────────────────────────────────────────────────
    nav_items = [
        ("🏠",  "Home",           "home",     "#555577"),
        ("🎙️",  "Hey Girl",       "heygirl",  NEON_PINK),
        ("🖥️",  "Computer Use",   "compuse",  NEON_PURPLE),
        ("📝",  "AutoFormFiller", "autoform", NEON_CYAN),
        ("⚙️",  "Settings",       "settings", "#8888aa"),
    ]

    active_btn: dict = {"ref": None, "indicator": None}

    for icon, label, key, color in nav_items:
        row = tk.Frame(sidebar, bg=SIDEBAR_BG, cursor="hand2")
        row.pack(fill=tk.X, padx=8, pady=2)

        indicator = tk.Frame(row, bg=SIDEBAR_BG, width=4)
        indicator.pack(side=tk.LEFT, fill=tk.Y, pady=2)

        icon_lbl = tk.Label(row, text=icon, font=("Segoe UI Emoji", 13),
                             bg=SIDEBAR_BG, fg=color, width=3)
        icon_lbl.pack(side=tk.LEFT)

        text_lbl = tk.Label(row, text=label, font=F_MAIN, anchor="w",
                             bg=SIDEBAR_BG, fg=TEXT_FG)
        text_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=8)

        def _click(k=key, r=row, ind=indicator, c=color,
                   il=icon_lbl, tl=text_lbl):
            if active_btn["ref"]:
                prev = active_btn["ref"]
                prev["row"].config(bg=SIDEBAR_BG)
                prev["ind"].config(bg=SIDEBAR_BG)
                prev["il"].config(bg=SIDEBAR_BG)
                prev["tl"].config(bg=SIDEBAR_BG, fg=TEXT_FG)
            r.config(bg=lerp_color(c, BG, 0.8))
            ind.config(bg=c)
            il.config(bg=lerp_color(c, BG, 0.8))
            tl.config(bg=lerp_color(c, BG, 0.8), fg="white")
            active_btn["ref"] = {"row": r, "ind": ind, "il": il, "tl": tl}
            show(k)

        for widget in (row, icon_lbl, text_lbl):
            widget.bind("<Button-1>", lambda e, fn=_click: fn())
            widget.bind("<Enter>",
                lambda e, r=row, c=color:
                    r.config(bg=lerp_color(c, BG, 0.88)))
            widget.bind("<Leave>",
                lambda e, r=row, fn=_click:
                    None)   # actual restore happens on click

        if key == "home":
            _click()

    tk.Frame(sidebar, bg=BORDER, height=1).pack(fill=tk.X, padx=12, pady=(16, 0))
    tk.Label(sidebar, text="v1.0  ·  MLEbotics",
             bg=SIDEBAR_BG, fg=MUTED, font=("Segoe UI", 8)).pack(side=tk.BOTTOM, pady=10)

    def on_close():
        srv = _flask_server["ref"]
        if srv:
            srv.shutdown()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
