"""
Hey Girl — D2L Brightspace Quiz Solver
Automatically reads quiz questions, answers them using AI, and submits.
Works with Bow Valley College D2L (Brightspace) quizzes.
"""

import time
import os
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager
import anthropic

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

QUIZ_URL = "https://d2l.bowvalleycollege.ca/d2l/lms/quizzing/user/attempt/quiz_start_frame_auto.d2l?ou=462536&isprv=&qi=532555&cfql=0&dnb=0&fromQB=0&inProgress=0"


def ask_ai(question: str, options: list = None) -> str:
    """Use Claude to answer a programming/coding question."""
    prompt = f"You are a programming and coding expert. Answer the following quiz question accurately and concisely.\n\nQuestion: {question}\n"
    if options:
        prompt += "\nOptions:\n"
        for i, opt in enumerate(options):
            prompt += f"  {chr(65+i)}. {opt}\n"
        prompt += "\nRespond with ONLY the exact text of the correct option (copy it exactly as written above). Do not add any explanation."
    else:
        prompt += "\nProvide a concise, correct answer."

    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text.strip()


def get_driver():
    """Create and return a Chrome WebDriver."""
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-notifications")
    # Use existing Chrome profile so you stay logged in
    user_data = os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data")
    if os.path.exists(user_data):
        options.add_argument(f"--user-data-dir={user_data}")
        options.add_argument("--profile-directory=Default")
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )
    return driver


def extract_questions(driver):
    """Extract all questions and their answer options from the current page."""
    wait = WebDriverWait(driver, 15)
    questions = []

    # D2L question containers
    try:
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".d2l-question, [class*='question']")))
    except Exception:
        pass

    # Try multiple D2L question selectors
    q_containers = driver.find_elements(By.CSS_SELECTOR,
        ".d2l-question, .d2l-htmlblock-untrusted, [class*='qnContent'], [class*='QuestionContent']"
    )

    if not q_containers:
        # Fallback: find all fieldsets (radio groups) or list items
        q_containers = driver.find_elements(By.CSS_SELECTOR, "fieldset, .d2l-shuffle-list")

    print(f"[Quiz] Found {len(q_containers)} question blocks on this page.")

    for idx, container in enumerate(q_containers):
        try:
            # Get question text
            q_text_el = container.find_elements(By.CSS_SELECTOR,
                ".d2l-element-text, .qnContent, p, label, .d2l-htmlblock, span"
            )
            q_text = ""
            for el in q_text_el:
                txt = el.text.strip()
                if txt and len(txt) > 10:
                    q_text = txt
                    break

            if not q_text:
                q_text = container.text.strip()

            # Get radio/checkbox options
            radio_inputs = container.find_elements(By.CSS_SELECTOR, "input[type='radio'], input[type='checkbox']")
            options = []
            option_elements = []
            for r in radio_inputs:
                # Get label text for this input
                try:
                    label = driver.find_element(By.CSS_SELECTOR, f"label[for='{r.get_attribute('id')}']")
                    label_text = label.text.strip()
                except Exception:
                    label_text = r.get_attribute("value") or ""
                if label_text:
                    options.append(label_text)
                    option_elements.append(r)

            # Text input (written answer)
            text_inputs = container.find_elements(By.CSS_SELECTOR, "input[type='text'], textarea")

            questions.append({
                "index": idx,
                "text": q_text,
                "options": options,
                "option_elements": option_elements,
                "text_inputs": text_inputs,
                "container": container,
            })
            print(f"  Q{idx+1}: {q_text[:80]}... | Options: {options}")
        except Exception as e:
            print(f"  [Warning] Could not parse question {idx+1}: {e}")

    return questions


def answer_question(driver, q: dict):
    """Use AI to determine and select the correct answer for a question."""
    question_text = q["text"]
    options = q["options"]
    option_elements = q["option_elements"]
    text_inputs = q["text_inputs"]

    print(f"\n[Quiz] Answering: {question_text[:100]}")

    if options and option_elements:
        # Multiple choice / True-False
        ai_answer = ask_ai(question_text, options)
        print(f"  AI Answer: {ai_answer}")

        # Find the best matching option
        best_idx = 0
        best_score = 0
        ai_lower = ai_answer.lower()
        for i, opt in enumerate(options):
            opt_lower = opt.lower()
            # Score by overlap
            score = sum(1 for word in ai_lower.split() if word in opt_lower)
            # Exact match gets highest score
            if ai_lower in opt_lower or opt_lower in ai_lower:
                score += 100
            if score > best_score:
                best_score = score
                best_idx = i

        try:
            el = option_elements[best_idx]
            driver.execute_script("arguments[0].scrollIntoView(true);", el)
            time.sleep(0.3)
            driver.execute_script("arguments[0].click();", el)
            print(f"  Selected option {best_idx+1}: {options[best_idx]}")
        except Exception as e:
            print(f"  [Error] Could not click option: {e}")

    elif text_inputs:
        # Written answer question
        ai_answer = ask_ai(question_text)
        print(f"  AI Written Answer: {ai_answer}")
        try:
            inp = text_inputs[0]
            driver.execute_script("arguments[0].scrollIntoView(true);", inp)
            time.sleep(0.2)
            inp.clear()
            inp.send_keys(ai_answer)
        except Exception as e:
            print(f"  [Error] Could not type answer: {e}")
    else:
        print(f"  [Skip] No answerable inputs found for this question.")


def scroll_and_answer_all(driver):
    """Scroll through the page and answer all questions."""
    questions = extract_questions(driver)
    if not questions:
        print("[Quiz] No questions found on this page. Make sure the quiz is open.")
        return False

    for q in questions:
        answer_question(driver, q)
        time.sleep(0.5)

    return True


def navigate_and_submit(driver):
    """Click Next/Submit until the quiz is complete."""
    wait = WebDriverWait(driver, 10)
    page = 1
    while True:
        print(f"\n[Quiz] === Page {page} ===")
        # Answer all questions on current page
        answered = scroll_and_answer_all(driver)

        time.sleep(1)

        # Look for Next button
        next_btn = None
        for selector in [
            "input[value*='Next'], input[value*='next']",
            "button[class*='next'], button[class*='Next']",
            "[class*='d2l-button'][class*='next']",
            "input[type='submit'][value*='Next']",
        ]:
            els = driver.find_elements(By.CSS_SELECTOR, selector)
            if els:
                next_btn = els[0]
                break

        # Look for Submit/Finish button
        submit_btn = None
        for selector in [
            "input[value*='Submit'], input[value*='Finish'], input[value*='submit']",
            "button[class*='submit'], button[class*='Submit']",
            "input[type='submit'][value*='Submit']",
            "input[type='submit'][value*='Finish Quiz']",
            "[class*='d2l-button'][class*='submit']",
        ]:
            els = driver.find_elements(By.CSS_SELECTOR, selector)
            if els:
                submit_btn = els[0]
                break

        if next_btn:
            print(f"[Quiz] Clicking Next...")
            driver.execute_script("arguments[0].scrollIntoView(true);", next_btn)
            time.sleep(0.5)
            driver.execute_script("arguments[0].click();", next_btn)
            time.sleep(2)
            page += 1
        elif submit_btn:
            print(f"[Quiz] Clicking Submit/Finish...")
            driver.execute_script("arguments[0].scrollIntoView(true);", submit_btn)
            time.sleep(0.5)
            driver.execute_script("arguments[0].click();", submit_btn)
            time.sleep(2)

            # Confirm submission dialog if present
            try:
                confirm = driver.find_element(By.CSS_SELECTOR,
                    "input[value*='Submit'], button[class*='confirm'], .d2l-dialog-confirm"
                )
                driver.execute_script("arguments[0].click();", confirm)
                print("[Quiz] Confirmed submission.")
            except Exception:
                pass
            print("[Quiz] Quiz submitted!")
            break
        else:
            print("[Quiz] No Next or Submit button found. Stopping.")
            break


def solve_quiz(url: str = QUIZ_URL):
    """Main function: open quiz, answer all questions, and submit."""
    print(f"\n[Hey Girl - Quiz Solver] Opening quiz: {url}")
    driver = get_driver()

    try:
        driver.get(url)
        print("[Quiz] Page loaded. Waiting for quiz content...")
        time.sleep(3)

        # Check if login is needed
        if "login" in driver.current_url.lower() or "signin" in driver.current_url.lower():
            print("[Quiz] Please log in to D2L in the browser window that opened.")
            print("[Quiz] Waiting up to 60 seconds for you to log in...")
            WebDriverWait(driver, 60).until(
                lambda d: "login" not in d.current_url.lower() and "signin" not in d.current_url.lower()
            )
            print("[Quiz] Logged in! Navigating to quiz...")
            driver.get(url)
            time.sleep(3)

        # Start the quiz if there's a Start button
        try:
            start_btn = driver.find_element(By.CSS_SELECTOR,
                "input[value*='Start'], button[class*='start'], input[value*='Begin']"
            )
            print("[Quiz] Clicking Start Quiz button...")
            driver.execute_script("arguments[0].click();", start_btn)
            time.sleep(2)
        except Exception:
            pass

        # Navigate and answer all questions
        navigate_and_submit(driver)

        print("\n[Hey Girl] Quiz complete!")
        input("Press Enter to close the browser...")
    except Exception as e:
        print(f"[Quiz Error] {e}")
        input("Press Enter to close the browser...")
    finally:
        driver.quit()


if __name__ == "__main__":
    solve_quiz()
