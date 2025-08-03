# ghost_support_bot.py
import asyncio
from playwright.async_api import async_playwright, Error as PlaywrightError
import subprocess
import psutil
import tempfile

browser_url = "http://localhost:9222"
playwright = None
browser = None
context = None
user_tabs = {}

GHOST_URL = "https://chatgpt.com/g/g-688ae39cff3881919cd9646c25a18e3d-ghost-support"

import sys

async def shutdown():
    global playwright, browser
    if browser:
        await browser.close()
    if playwright:
        await playwright.stop()


def is_chrome_debugging():
    for proc in psutil.process_iter(attrs=["name", "cmdline"]):
        try:
            if "chrome.exe" in proc.info["name"].lower():
                if "--remote-debugging-port=9222" in " ".join(proc.info["cmdline"]):
                    return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return False


import os
import platform

TEMP_PROFILE = os.path.join(tempfile.gettempdir(), "chrome-cdp-profile")

def launch_chrome_with_debugging():
    
    CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    
    if platform.system() == "Darwin":
        CHROME_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

    subprocess.Popen([
        CHROME_PATH,
        "--remote-debugging-port=9222",
        f"--user-data-dir={TEMP_PROFILE}",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-popup-blocking",
        "--new-window"
    ])
    print(f"🟢 New Chrome Window launched with temp profile at: {TEMP_PROFILE}")


async def init_browser():
    global playwright, browser, context

    if not is_chrome_debugging():
        launch_chrome_with_debugging()
        await asyncio.sleep(3)

    if not playwright:
        playwright = await async_playwright().start()

    for attempt in range(5):
        try:
            browser = await playwright.chromium.connect_over_cdp(browser_url)
            break
        except PlaywrightError as e:
            print(f"⏳ Attempt {attempt + 1}/5: CDP connect failed: {e}")
            await asyncio.sleep(1)
    else:
        print("❌ Failed to connect to Chrome after multiple attempts.")
        return

    context = browser.contexts[0] if browser.contexts else await browser.new_context()


async def open_tab_for_user(user_id):
    await init_browser()

    if context is not None:
        page = await context.new_page()
        response = await page.goto(GHOST_URL)

        if response is not None and response.status == 404:
            print("❌ Access denied (404). Application host must be logged in to ChatGPT.")
            await shutdown()
            sys.exit()

        print("✅ Logged in session detected. Proceeding...")
        user_tabs[user_id] = page

async def close_tab_for_user(user_id):
    page = user_tabs.pop(user_id, None)
    if page:
        await page.close()


async def send_prompt(user_id, prompt):
    async def _send(page):
        await page.wait_for_selector('p[data-placeholder="Ask anything"]', timeout=10000)
        await page.click('p[data-placeholder="Ask anything"]')
        await page.keyboard.type(prompt)
        await page.keyboard.press("Enter")

    page = user_tabs.get(user_id)
    if not page:
        return "[!] No active session."

    try:
        await _send(page)
    except PlaywrightError:
        print("[!] TargetClosedError: Reinitializing tab...")
        # Reinitialize the tab
        await open_tab_for_user(user_id)
        page = user_tabs.get(user_id)
        if not page:
            return "[!] Failed to reopen tab after crash."
        try:
            await _send(page)
        except Exception as e:
            return f"[!] Failed to resend prompt after recovery: {e}"

    return "✅ Prompt sent."

async def is_responding(page):
    return await page.evaluate("""
        () => {
            const btn = document.querySelector('#composer-submit-button');
            return btn?.getAttribute('aria-label') === 'Stop streaming';
        }
    """)

async def get_latest_response(user_id):
    page = user_tabs.get(user_id)
    if not page:
        return "[!] No active session."

    # Wait while it's streaming
    while await is_responding(page):
        await asyncio.sleep(0.1)

         # Extract text from <code> blocks in the latest assistant turn
    result = await page.evaluate("""
    () => {
        const assistantBlocks = document.querySelectorAll('[data-turn="assistant"]');
        if (!assistantBlocks.length) return "[!] No assistant response found.";

        const latest = assistantBlocks[assistantBlocks.length - 1];
        const codeBlocks = latest.querySelectorAll('code');
        if (!codeBlocks.length) return "[!] No code block in last response.";

        return Array.from(codeBlocks).map(code => code.innerText.trim()).join("\\n\\n");
    }
    """)

    return result



def start():
    print("[✓] Ghost Support Sytem Ready")
