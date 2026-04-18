"""
Main Orchestrator — Hey Girl AI Assistant
Routes tasks to Claude (desktop) or OpenAI CUA (web) automatically.
Supports always-on wake word ("hey girl"), web search, voice chat, and GUI.
"""

from router import classify
from memory import get_summary, clear as clear_memory, add_to_history, get_conversation_history
from agent import run_agent, speak, listen, web_search, start_wake_listener, stop_wake_listener


def run(task: str, max_steps: int = 20, history: list = None):
    """Route and execute a task using the appropriate agent."""

    print(f"\n{'='*60}")
    print(f"Task: {task}")
    print(f"{'='*60}")

    # Show recent activity context
    summary = get_summary()
    if summary != "No previous activity.":
        print(f"\n[Memory] Recent activity:\n{summary}\n")

    # Handle simple knowledge/search questions directly
    question_keywords = ["what is", "what are", "who is", "how does", "explain", "define", "tell me about", "search for"]
    if any(task.lower().startswith(kw) for kw in question_keywords):
        print("[Orchestrator] Answering with web search...")
        answer = web_search(task)
        print(f"[Hey Girl] {answer}")
        speak(answer)
        return answer

    # Classify task
    agent_type = classify(task)

    if agent_type == "web":
        print("[Orchestrator] Routing to OpenAI CUA (web task)")
        try:
            from openai_agent import run_agent
            result = run_agent(task, max_steps=max_steps)
        except (ValueError, Exception) as e:
            print(f"[Orchestrator] OpenAI CUA unavailable: {e}")
            print("[Orchestrator] Falling back to Claude for this task...")
            from agent import run_agent as claude_run
            result = claude_run(task, max_steps=max_steps, history=history)
    else:
        print("[Orchestrator] Routing to Claude Computer Use (desktop task)")
        from agent import run_agent as claude_run
        result = claude_run(task, max_steps=max_steps, history=history)

    return result


def handle_voice_command(command: str):
    """Callback for wake word listener - process a voice command."""
    if not command:
        return
    print(f"\n[Hey Girl] Voice command: {command}")
    add_to_history("user", command)
    result = run(command, history=get_conversation_history())
    add_to_history("assistant", result or "")
    if result:
        speak(str(result))


def main():
    print("\n╔══════════════════════════════════════════╗")
    print("║        Hey Girl — AI Assistant           ║")
    print("║  Voice • Web • Desktop • Automation      ║")
    print("╚══════════════════════════════════════════╝")
    print("\nCommands:")
    print("  Type a task or question to execute it")
    print("  'wake'     - start always-on 'hey girl' voice listener")
    print("  'voice'    - toggle manual push-to-talk voice mode")
    print("  'search X' - search the web for X")
    print("  'gui'      - launch desktop GUI")
    print("  'history'  - show recent agent activity")
    print("  'clear'    - clear memory log")
    print("  'quit'     - exit\n")

    speak("Hey girl is ready. How can I help you?")

    voice_mode = False
    wake_active = False

    QUIZ_URL = "https://d2l.bowvalleycollege.ca/d2l/lms/quizzing/user/attempt/quiz_start_frame_auto.d2l?ou=462536&isprv=&qi=532555&cfql=0&dnb=0&fromQB=0&inProgress=0"

    while True:
        try:
            if voice_mode:
                speak("Say your command.")
                user_input = listen()
                if not user_input:
                    continue
                print(f"You said: {user_input}")
            else:
                user_input = input("Task> ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            stop_wake_listener()
            break

        if not user_input:
            continue
        elif user_input.lower() == "quit":
            stop_wake_listener()
            break
        elif user_input.lower() == "history":
            print(get_summary())
        elif user_input.lower() == "clear":
            clear_memory()
        elif user_input.lower() == "voice":
            voice_mode = not voice_mode
            status = "enabled" if voice_mode else "disabled"
            print(f"Voice mode {status}.")
            speak(f"Voice mode {status}.")
        elif user_input.lower() == "wake":
            if not wake_active:
                wake_active = True
                start_wake_listener(handle_voice_command)
                speak("Always-on mode enabled. Say 'hey girl' followed by your command.")
            else:
                stop_wake_listener()
                wake_active = False
                speak("Always-on mode disabled.")
        elif user_input.lower().startswith("search "):
            query = user_input[7:]
            answer = web_search(query)
            print(f"[Hey Girl] {answer}")
            speak(answer)
        elif any(kw in user_input.lower() for kw in ["take quiz", "solve quiz", "do quiz", "answer quiz", "start quiz"]):
            speak("Starting quiz solver. Opening your D2L quiz now.")
            import threading
            from quiz_solver import solve_quiz
            threading.Thread(target=solve_quiz, args=(QUIZ_URL,), daemon=True).start()
        elif any(kw in user_input.lower() for kw in ["read assignment", "what is my assignment", "check assignment", "open assignment", "tell me about the assignment", "what is the assignment"]):
            speak("Sure! Let me read your D2L assignment and open it in VS Code with Copilot.")
            import threading
            from assignment_reader import read_assignment
            threading.Thread(target=read_assignment, kwargs={"speak_fn": speak}, daemon=True).start()
        elif user_input.lower() == "gui":
            try:
                import gui
                gui.launch()
            except Exception as e:
                print(f"GUI error: {e}")
        else:
            add_to_history("user", user_input)
            result = run(user_input, history=get_conversation_history())
            add_to_history("assistant", result or "")
            if (voice_mode or wake_active) and result:
                speak(str(result))

if __name__ == "__main__":
    main()
