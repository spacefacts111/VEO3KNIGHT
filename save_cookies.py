import json
import time
from playwright.sync_api import sync_playwright

COOKIES_FILE = "cookies.json"

def save_gemini_cookies():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--start-maximized"
            ]
        )
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800}
        )

        page = context.new_page()
        print("🌐 Opening Gemini login page...")
        page.goto("https://gemini.google.com/app")
        print("➡️ Log in manually, then navigate to Veo 3 page.")
        page.goto("https://gemini.google.com/app/veo")
        input("✅ Press Enter HERE after you’re fully logged in and the Veo 3 prompt box is visible...")
        cookies = context.cookies()
        with open(COOKIES_FILE, "w") as f:
            json.dump(cookies, f)
        print(f"✅ Cookies saved successfully to {COOKIES_FILE}")
        browser.close()

if __name__ == "__main__":
    save_gemini_cookies()
