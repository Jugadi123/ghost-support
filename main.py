from playwright.sync_api import sync_playwright
import random
import time
import threading
import keyboard  # pip install keyboard

# === Prompt Bank ===
prompts = [
    "What’s a productivity hack you think everyone should know?",
    "Summarize this webpage in a single sentence.",
    "Pretend you’re my AI assistant — what do I need to do today?",
    "Translate this sentence into pirate speak.",
    "Give me a controversial opinion in 10 words or less."
]

# === Panic Exit ===
def panic_listener():
    keyboard.wait("end")
    print("[!] Panic key pressed. Exiting.")
    exit(0)

threading.Thread(target=panic_listener, daemon=True).start()

# === Main Logic ===
with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://localhost:9222")
    context = browser.contexts[0]

    # Find the ChatGPT tab
    page = None
    for pg in context.pages:
        if "chatgpt.com" in pg.url:
            page = pg
            break

    if not page:
        raise RuntimeError("[X] Could not find a ChatGPT tab.")

    def is_gpt_responding(page):
        return page.evaluate("""
            () => {
                const btn = document.querySelector('#composer-submit-button');
                return btn?.getAttribute('aria-label') === 'Stop streaming';
            }
        """)

    def get_latest_response(page):
        return page.evaluate("""
        () => {
            const assistantBlocks = Array.from(document.querySelectorAll('[data-turn="assistant"]'));
            if (assistantBlocks.length === 0) return null;

            const latest = assistantBlocks[assistantBlocks.length - 1];
            const chunks = latest.querySelectorAll('[data-start][data-end]');
            
            return Array.from(chunks)
                .map(el => el.innerText.trim())
                .filter(Boolean)
                .join("\\n");
        }
        """)

    def send_prompt(page, prompt):
        try:
            page.wait_for_selector('p[data-placeholder="Ask anything"]', timeout=10000)
            page.click('p[data-placeholder="Ask anything"]')
            page.keyboard.type(prompt)
            page.keyboard.press("Enter")
        except Exception as e:
            print(f"[!] Error sending prompt: {e}")

    print("[✓] Connected to ChatGPT tab. Ready to chat.\n")

    while True:
        prompt = random.choice(prompts)
        print(f"user said: {prompt}")
        send_prompt(page, prompt)

        # Wait until GPT starts streaming
        time.sleep(1)
        while is_gpt_responding(page):
            print("[~] GPT is responding...")
            time.sleep(1)

        # Get the response
        response = get_latest_response(page)
        if response:
            print(f"gpt said:\n{response}\n")
        else:
            print("[!] No response found.\n")

        # Short delay before next prompt
        time.sleep(2)
