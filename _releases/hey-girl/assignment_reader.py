"""
Hey Girl — D2L Assignment Reader & VS Code Helper
Reads the D2L course/assignment page, summarizes it with AI,
then opens VS Code and uses Copilot to help complete the assignment.
"""

import time
import os
import re
import subprocess
import tempfile
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import anthropic

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# Bow Valley College D2L course base URL
COURSE_ID = "462536"
COURSE_HOME = f"https://d2l.bowvalleycollege.ca/d2l/home/{COURSE_ID}"
ASSIGNMENTS_URL = f"https://d2l.bowvalleycollege.ca/d2l/lms/dropbox/user/folders_list.d2l?ou={COURSE_ID}&isprv=0"
CONTENT_URL = f"https://d2l.bowvalleycollege.ca/d2l/le/content/{COURSE_ID}/home"


def get_driver():
    """Create and return a Chrome WebDriver using existing login session."""
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-notifications")
    user_data = os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data")
    if os.path.exists(user_data):
        options.add_argument(f"--user-data-dir={user_data}")
        options.add_argument("--profile-directory=Default")
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )
    return driver


def wait_for_login(driver, url):
    """Navigate to URL, wait for login if needed."""
    driver.get(url)
    time.sleep(3)
    if "login" in driver.current_url.lower() or "signin" in driver.current_url.lower():
        print("[Hey Girl] Please log in to D2L in the browser window.")
        print("[Hey Girl] Waiting up to 90 seconds for login...")
        WebDriverWait(driver, 90).until(
            lambda d: "login" not in d.current_url.lower() and "signin" not in d.current_url.lower()
        )
        driver.get(url)
        time.sleep(3)


def scrape_page_text(driver, max_chars=8000):
    """Extract all visible text from the current page."""
    try:
        body = driver.find_element(By.TAG_NAME, "body")
        text = body.text.strip()
        # Clean up excessive whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r' {2,}', ' ', text)
        return text[:max_chars]
    except Exception as e:
        return f"[Could not extract page text: {e}]"


def get_assignment_links(driver):
    """Find assignment/dropbox links on the page."""
    links = []
    for a in driver.find_elements(By.TAG_NAME, "a"):
        href = a.get_attribute("href") or ""
        text = a.text.strip()
        if text and ("assignment" in text.lower() or "dropbox" in href or "content" in href or "quiz" in href):
            links.append({"text": text, "href": href})
    return links[:10]


def summarize_with_ai(page_text: str, page_title: str = "") -> dict:
    """Use Claude to read the page and return a structured summary."""
    prompt = f"""You are an expert academic assistant. Read the following content from a Bow Valley College D2L course page and provide:

1. **What this page/course/assignment is about** (2-3 sentences)
2. **What the student needs to do** (bullet points of specific tasks)
3. **Programming language or tools required** (if any)
4. **Deadline or important dates** (if mentioned)
5. **Starter code or file names** (if mentioned)
6. **Suggested approach** to complete the assignment

Page Title: {page_title}

Page Content:
{page_text}

Respond in a clear, friendly, helpful tone as if you're a tutor explaining the assignment to a student."""

    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}]
    )
    summary = response.content[0].text.strip()

    # Also extract code-related info
    code_prompt = f"""Based on the assignment description below, generate:
1. A starter Python (or appropriate language) file with all required functions/classes stubbed out and comments explaining what each part should do.
2. Use TODO comments where the student needs to fill in logic.

Assignment:
{page_text[:3000]}

Return only the code, no explanation."""

    code_response = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=2000,
        messages=[{"role": "user", "content": code_prompt}]
    )
    starter_code = code_response.content[0].text.strip()
    # Clean markdown code fences if present
    starter_code = re.sub(r'^```[a-z]*\n?', '', starter_code, flags=re.MULTILINE)
    starter_code = re.sub(r'^```$', '', starter_code, flags=re.MULTILINE)

    return {"summary": summary, "starter_code": starter_code}


def open_in_vscode(code: str, filename: str = "assignment_starter.py", summary: str = ""):
    """Create a file with starter code and open it in VS Code with Copilot context."""
    # Create assignment folder on Desktop
    desktop = os.path.join(os.path.expanduser("~"), "Desktop", "hey_girl_assignments")
    os.makedirs(desktop, exist_ok=True)
    filepath = os.path.join(desktop, filename)

    # Write summary as a comment header + starter code
    header = f"# Assignment Summary (generated by Hey Girl)\n"
    header += "#\n"
    for line in summary.splitlines()[:30]:
        header += f"# {line}\n"
    header += "#\n\n"

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(header + code)

    print(f"[Hey Girl] Starter file created: {filepath}")

    # Open VS Code
    try:
        subprocess.Popen(["code", filepath])
        print("[Hey Girl] Opened in VS Code.")
        time.sleep(2)
        # Trigger Copilot Chat with context
        # (VS Code will open with the file; user can press Ctrl+Shift+I for Copilot Chat)
        import pyautogui
        pyautogui.hotkey('ctrl', 'shift', 'i')   # Open GitHub Copilot Chat
        time.sleep(1)
        # Type a prompt into Copilot Chat
        copilot_prompt = "Hey, I have an assignment. Can you help me understand and complete this code? I've added comments explaining what each function should do."
        pyautogui.typewrite(copilot_prompt, interval=0.03)
        pyautogui.press('enter')
        print("[Hey Girl] Copilot Chat triggered.")
    except FileNotFoundError:
        print("[Hey Girl] VS Code not found in PATH. Opening file with default editor...")
        os.startfile(filepath)
    except Exception as e:
        print(f"[Hey Girl] Error opening VS Code: {e}")

    return filepath


def read_assignment(url: str = None, speak_fn=None):
    """
    Main function: open D2L, read the assignment/course page,
    summarize it, open VS Code with starter code, and trigger Copilot.
    """
    def say(text):
        print(f"[Hey Girl] {text}")
        if speak_fn:
            speak_fn(text)

    say("Sure! Let me open your D2L course and read your assignment for you.")
    driver = get_driver()

    try:
        # 1. Go to course home or provided URL
        target = url or CONTENT_URL
        wait_for_login(driver, target)
        page_title = driver.title
        say(f"Opened: {page_title}")

        # 2. Scrape main content
        page_text = scrape_page_text(driver)

        # 3. Check for assignment links and follow the most relevant one
        links = get_assignment_links(driver)
        if links:
            say(f"Found {len(links)} course links. Checking for assignments...")
            for link in links:
                say(f"  - {link['text']}")
            # Follow first assignment-related link
            best = next((l for l in links if "assignment" in l["text"].lower() or "dropbox" in l["href"]), links[0])
            if best["href"]:
                driver.get(best["href"])
                time.sleep(2)
                page_text += "\n\n" + scrape_page_text(driver)
                page_title = driver.title

        # 4. Summarize with AI
        say("Reading and analyzing the assignment content with AI...")
        result = summarize_with_ai(page_text, page_title)
        summary = result["summary"]
        starter_code = result["starter_code"]

        # 5. Print and speak the summary
        print("\n" + "="*60)
        print("ASSIGNMENT SUMMARY")
        print("="*60)
        print(summary)
        print("="*60 + "\n")
        say("Here is what I found about your assignment:")
        # Speak a short version (first 500 chars)
        short_summary = summary[:500].replace("#", "").replace("*", "").replace("\n", " ")
        if speak_fn:
            speak_fn(short_summary)

        # 6. Open in VS Code with starter code + Copilot
        safe_title = re.sub(r'[^a-zA-Z0-9_]', '_', page_title[:30].lower())
        filename = f"{safe_title or 'assignment'}_starter.py"
        filepath = open_in_vscode(starter_code, filename, summary)

        say(f"I've created a starter file at {filepath} and opened it in VS Code. Copilot has been triggered to help you!")

        input("\n[Hey Girl] Press Enter to close the browser...")
        return summary

    except Exception as e:
        say(f"Sorry, I ran into an error: {e}")
        print(f"[Error] {e}")
        input("Press Enter to close the browser...")
        return None
    finally:
        driver.quit()


if __name__ == "__main__":
    read_assignment()
