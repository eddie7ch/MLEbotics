"""
Hey Girl — Desktop GUI
A modern chat-style interface for the Hey Girl AI assistant.
Features: chat history, voice toggle, always-on wake word, web search.
"""

import tkinter as tk
from tkinter import scrolledtext, ttk
import threading


def launch():
    """Launch the Hey Girl desktop GUI."""
    from agent import speak, listen, web_search, start_wake_listener, stop_wake_listener
    from main import run, handle_voice_command
    from memory import add_to_history, get_conversation_history, clear as clear_memory

    root = tk.Tk()
    root.title("Hey Girl — AI Assistant")
    root.geometry("700x600")
    root.configure(bg="#1a1a2e")
    root.resizable(True, True)

    # --- Fonts & Colors ---
    BG = "#1a1a2e"
    PANEL = "#16213e"
    ACCENT = "#e94560"
    TEXT_FG = "#eaeaea"
    USER_FG = "#a8d8ea"
    BOT_FG = "#ffcb77"
    ENTRY_BG = "#0f3460"
    BTN_BG = "#e94560"
    BTN_FG = "#ffffff"
    FONT_MAIN = ("Segoe UI", 11)
    FONT_BOLD = ("Segoe UI", 11, "bold")
    FONT_TITLE = ("Segoe UI", 14, "bold")

    # --- Title Bar ---
    title_frame = tk.Frame(root, bg=ACCENT, pady=8)
    title_frame.pack(fill=tk.X)
    tk.Label(title_frame, text="✨ Hey Girl", font=FONT_TITLE, bg=ACCENT, fg="white").pack(side=tk.LEFT, padx=16)
    tk.Label(title_frame, text="AI Assistant · Voice · Web · Desktop Control", font=("Segoe UI", 9), bg=ACCENT, fg="#ffe0e0").pack(side=tk.LEFT)

    # --- Status bar ---
    status_var = tk.StringVar(value="Ready")
    status_bar = tk.Label(root, textvariable=status_var, bg=PANEL, fg="#aaaaaa", font=("Segoe UI", 9), anchor="w", padx=10)
    status_bar.pack(fill=tk.X)

    # --- Chat Area ---
    chat_frame = tk.Frame(root, bg=BG)
    chat_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(8, 4))

    chat_area = scrolledtext.ScrolledText(
        chat_frame, wrap=tk.WORD, font=FONT_MAIN,
        bg=PANEL, fg=TEXT_FG, insertbackground=TEXT_FG,
        relief=tk.FLAT, bd=0, padx=10, pady=10, state=tk.DISABLED
    )
    chat_area.pack(fill=tk.BOTH, expand=True)
    chat_area.tag_config("user", foreground=USER_FG, font=FONT_BOLD)
    chat_area.tag_config("bot", foreground=BOT_FG, font=FONT_MAIN)
    chat_area.tag_config("system", foreground="#888888", font=("Segoe UI", 9, "italic"))

    def append_chat(sender, message, tag="bot"):
        chat_area.configure(state=tk.NORMAL)
        if sender:
            chat_area.insert(tk.END, f"\n{sender}: ", tag)
        chat_area.insert(tk.END, f"{message}\n", tag)
        chat_area.configure(state=tk.DISABLED)
        chat_area.see(tk.END)

    append_chat(None, "Hey Girl is online. Type or speak your command!", "system")

    # --- Input Area ---
    input_frame = tk.Frame(root, bg=BG, pady=6)
    input_frame.pack(fill=tk.X, padx=10)

    entry = tk.Entry(
        input_frame, font=FONT_MAIN, bg=ENTRY_BG, fg=TEXT_FG,
        insertbackground=TEXT_FG, relief=tk.FLAT, bd=4
    )
    entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8), ipady=6)

    # --- Button Bar ---
    btn_frame = tk.Frame(root, bg=BG, pady=4)
    btn_frame.pack(fill=tk.X, padx=10, pady=(0, 8))

    voice_active = {"value": False}
    wake_active = {"value": False}

    def run_task_thread(task):
        """Run a task in a background thread so the GUI doesn't freeze."""
        status_var.set("Processing...")
        try:
            add_to_history("user", task)
            result = run(task, history=get_conversation_history())
            add_to_history("assistant", result or "")
            display = result if result else "Task complete."
            root.after(0, lambda: append_chat("Hey Girl", display, "bot"))
            root.after(0, lambda: speak(display))
        except Exception as e:
            root.after(0, lambda: append_chat("Error", str(e), "system"))
        finally:
            root.after(0, lambda: status_var.set("Ready"))

    def send_message(event=None):
        task = entry.get().strip()
        if not task:
            return
        entry.delete(0, tk.END)
        append_chat("You", task, "user")
        threading.Thread(target=run_task_thread, args=(task,), daemon=True).start()

    entry.bind("<Return>", send_message)

    send_btn = tk.Button(
        btn_frame, text="Send", command=send_message,
        bg=BTN_BG, fg=BTN_FG, font=FONT_BOLD, relief=tk.FLAT, padx=16, pady=4, cursor="hand2"
    )
    send_btn.pack(side=tk.LEFT, padx=(0, 6))

    def toggle_voice():
        if not voice_active["value"]:
            voice_active["value"] = True
            voice_btn.config(text="🎙 Stop", bg="#00b09b")
            status_var.set("Listening...")
            def voice_thread():
                result = listen(timeout=8, phrase_limit=15)
                voice_active["value"] = False
                root.after(0, lambda: voice_btn.config(text="🎙 Voice", bg="#444466"))
                if result:
                    root.after(0, lambda: entry.insert(0, result))
                    root.after(0, lambda: status_var.set("Ready"))
                else:
                    root.after(0, lambda: status_var.set("Didn't catch that. Try again."))
            threading.Thread(target=voice_thread, daemon=True).start()
        else:
            voice_active["value"] = False
            voice_btn.config(text="🎙 Voice", bg="#444466")
            status_var.set("Ready")

    voice_btn = tk.Button(
        btn_frame, text="🎙 Voice", command=toggle_voice,
        bg="#444466", fg=BTN_FG, font=FONT_MAIN, relief=tk.FLAT, padx=12, pady=4, cursor="hand2"
    )
    voice_btn.pack(side=tk.LEFT, padx=(0, 6))

    def toggle_wake():
        if not wake_active["value"]:
            wake_active["value"] = True
            wake_btn.config(text="👂 Listening...", bg="#f7971e")
            status_var.set("Always-on: say 'hey girl' + command")
            def wake_callback(command):
                root.after(0, lambda: append_chat("You (voice)", command, "user"))
                threading.Thread(target=run_task_thread, args=(command,), daemon=True).start()
            start_wake_listener(wake_callback)
            speak("Always-on mode enabled. Say hey girl to activate.")
        else:
            wake_active["value"] = False
            stop_wake_listener()
            wake_btn.config(text="👂 Wake Word", bg="#444466")
            status_var.set("Always-on mode disabled.")
            speak("Always-on mode disabled.")

    wake_btn = tk.Button(
        btn_frame, text="👂 Wake Word", command=toggle_wake,
        bg="#444466", fg=BTN_FG, font=FONT_MAIN, relief=tk.FLAT, padx=12, pady=4, cursor="hand2"
    )
    wake_btn.pack(side=tk.LEFT, padx=(0, 6))

    def do_search():
        query = entry.get().strip()
        if not query:
            return
        entry.delete(0, tk.END)
        append_chat("You", f"Search: {query}", "user")
        def search_thread():
            status_var.set("Searching...")
            result = web_search(query)
            root.after(0, lambda: append_chat("Hey Girl", result, "bot"))
            root.after(0, lambda: speak(result))
            root.after(0, lambda: status_var.set("Ready"))
        threading.Thread(target=search_thread, daemon=True).start()

    search_btn = tk.Button(
        btn_frame, text="🔍 Search", command=do_search,
        bg="#444466", fg=BTN_FG, font=FONT_MAIN, relief=tk.FLAT, padx=12, pady=4, cursor="hand2"
    )
    search_btn.pack(side=tk.LEFT, padx=(0, 6))

    QUIZ_URL = "https://d2l.bowvalleycollege.ca/d2l/lms/quizzing/user/attempt/quiz_start_frame_auto.d2l?ou=462536&isprv=&qi=532555&cfql=0&dnb=0&fromQB=0&inProgress=0"

    def do_quiz():
        append_chat("Hey Girl", "Opening your D2L quiz and solving it automatically...", "bot")
        speak("Starting quiz solver. Opening your D2L quiz now.")
        from quiz_solver import solve_quiz
        threading.Thread(target=solve_quiz, args=(QUIZ_URL,), daemon=True).start()

    quiz_btn = tk.Button(
        btn_frame, text="📝 Take Quiz", command=do_quiz,
        bg="#6a0dad", fg=BTN_FG, font=FONT_MAIN, relief=tk.FLAT, padx=12, pady=4, cursor="hand2"
    )
    quiz_btn.pack(side=tk.LEFT, padx=(0, 6))

    def do_read_assignment():
        append_chat("Hey Girl", "Opening your D2L course, reading your assignment, and setting up VS Code with Copilot...", "bot")
        speak("Let me read your assignment and open it in VS Code.")
        from assignment_reader import read_assignment
        def _run():
            result = read_assignment(speak_fn=speak)
            if result:
                short = result[:400].replace('#','').replace('*','').replace('\n',' ')
                root.after(0, lambda: append_chat("Hey Girl", result[:1200], "bot"))
        threading.Thread(target=_run, daemon=True).start()

    assign_btn = tk.Button(
        btn_frame, text="📚 Read Assignment", command=do_read_assignment,
        bg="#0077b6", fg=BTN_FG, font=FONT_MAIN, relief=tk.FLAT, padx=12, pady=4, cursor="hand2"
    )
    assign_btn.pack(side=tk.LEFT, padx=(0, 6))

    def do_clear():
        clear_memory()
        chat_area.configure(state=tk.NORMAL)
        chat_area.delete("1.0", tk.END)
        chat_area.configure(state=tk.DISABLED)
        append_chat(None, "Chat cleared.", "system")

    clear_btn = tk.Button(
        btn_frame, text="🗑 Clear", command=do_clear,
        bg="#444466", fg=BTN_FG, font=FONT_MAIN, relief=tk.FLAT, padx=12, pady=4, cursor="hand2"
    )
    clear_btn.pack(side=tk.LEFT)

    def on_close():
        stop_wake_listener()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    entry.focus_set()

    # Greet on open
    threading.Thread(target=lambda: speak("Hey girl is ready. How can I help you?"), daemon=True).start()

    root.mainloop()


if __name__ == "__main__":
    launch()
