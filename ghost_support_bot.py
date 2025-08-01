# ghost_support_bot.py
import asyncio
import clipboard
from playwright.async_api import async_playwright

browser_url = "http://localhost:9222"
playwright = None
browser = None
context = None
user_tabs = {}

async def init_browser():
    global playwright, browser, context
    if not playwright:
        playwright = await async_playwright().start()
        browser = await playwright.chromium.connect_over_cdp(browser_url)
        context = browser.contexts[0]

async def open_tab_for_user(user_id):
    await init_browser()
    if context is not None:
        page = await context.new_page()
        await page.goto("https://chatgpt.com/g/g-688ae39cff3881919cd9646c25a18e3d-ghost-support")
        user_tabs[user_id] = page

async def close_tab_for_user(user_id):
    page = user_tabs.pop(user_id, None)
    if page:
        await page.close()

async def send_prompt(user_id, prompt):
    page = user_tabs.get(user_id)
    if not page:
        return "[!] No active session."

    await page.wait_for_selector('p[data-placeholder="Ask anything"]', timeout=10000)
    await page.click('p[data-placeholder="Ask anything"]')
    await page.keyboard.type(prompt)
    await page.keyboard.press("Enter")

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

    # Try to copy the latest response
    clipboard.copy("")
    copied = await page.evaluate("""
    () => {
        const assistantBlocks = document.querySelectorAll('[data-turn="assistant"]');
        if (!assistantBlocks.length) return false;

        const latest = assistantBlocks[assistantBlocks.length - 1];
        const btn = latest.querySelector('button[aria-label="Copy"]');
        if (!btn) return false;

        btn.click();
        return true;
    }
    
    """)
    if not copied:
        return "[!] Couldn't copy response."
    
    # Wait for aria-label="Copied" confirmation
    for _ in range(50):  # ~5 seconds max
        status = await page.evaluate("""
            () => {
                const assistantBlocks = document.querySelectorAll('[data-turn="assistant"]');
                const latest = assistantBlocks[assistantBlocks.length - 1];
                const btn = latest?.querySelector('button[aria-label="Copied"]');
                return !!btn;
            }
        """)
        if status:
            break
        await asyncio.sleep(0.1)
    else:
        return "[!] Copy not confirmed by UI."

    # Retrieve clipboard
    for _ in range(30):  # ~3 seconds max
        result = clipboard.paste()
        if result:
            return result
        await asyncio.sleep(0.1)

    return "[!] Response copy timed out."

def start():
    print("[✓] Ghost Support Sytem Ready")
