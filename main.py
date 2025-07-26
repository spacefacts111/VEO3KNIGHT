import os
import time
import random
import json
import requests
import asyncio
from datetime import datetime
from instagrapi import Client
from playwright.async_api import async_playwright

SESSION_FILE = "session.json"
COOKIES_FILE = "cookies.json"
USERNAME = os.getenv("IG_USERNAME")
PASSWORD = os.getenv("IG_PASSWORD")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

def log(msg):
    print(f"{datetime.now().strftime('%H:%M:%S')} - {msg}", flush=True)

def upload_screenshot(file_path, label=""):
    try:
        with open(file_path, "rb") as f:
            r = requests.post("https://0x0.st", files={"file": f})
        if r.status_code == 200:
            link = r.text.strip()
            log(f"📸 Screenshot uploaded {label}: {link}")
            return link
        else:
            log(f"⚠️ Screenshot upload failed (status {r.status_code})")
    except Exception as e:
        log(f"⚠️ Screenshot upload failed: {e}")
    return None

def generate_ai_caption():
    prompt = (
        "Write a short, hard-hitting, sad or metaphorical quote that feels viral and relatable. "
        "Mix 60% heartbreak truths, 30% poetic metaphors, 10% thought-provoking questions. "
        "Max 15 words."
    )
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GOOGLE_API_KEY}"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        r = requests.post(url, json=payload, timeout=20)
        if r.status_code == 200:
            return r.json()["candidates"][0]["content"]["parts"][0]["text"]
    except:
        pass
    return random.choice([
        "Some things hurt more in silence.",
        "Rain hides my tears but not my pain."
    ])

def generate_ai_hashtags(caption):
    prompt = (
        f"Generate 8 to 12 Instagram hashtags for this caption: '{caption}'. "
        "Mix sad, poetic, relatable hashtags with 2-3 trending ones like #viral #fyp. "
        "Only return hashtags separated by spaces."
    )
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GOOGLE_API_KEY}"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        r = requests.post(url, json=payload, timeout=20)
        if r.status_code == 200:
            return r.json()["candidates"][0]["content"]["parts"][0]["text"]
    except:
        pass
    return "#sad #brokenhearts #viral #fyp #poetry"

async def generate_veo3_video(prompt):
    log(f"🎬 Starting Veo3 video generation for: {prompt}")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        if os.path.exists(COOKIES_FILE):
            cookies = json.load(open(COOKIES_FILE))
            await context.add_cookies(cookies)

        page = await context.new_page()
        log("⏳ Loading Veo 3 page...")
        await page.goto("https://gemini.google.com/app/veo")

        # Wait for textarea
        for _ in range(60):
            if await page.query_selector("textarea") or await page.query_selector("div[contenteditable='true']"):
                break
            await asyncio.sleep(1)

        target = await page.query_selector("textarea") or await page.query_selector("div[contenteditable='true']")
        if not target:
            await browser.close()
            raise Exception("❌ Could not find prompt field.")
        await target.click()
        await target.type(prompt, delay=50)

        # Screenshot BEFORE clicking
        before_file = "veo3_before_click.png"
        await page.screenshot(path=before_file)
        upload_screenshot(before_file, "(before clicking send)")

        # Click the REAL send button (paper-plane)
        log("🤖 Clicking Veo 3 send button...")
        clicked = False
        for attempt in range(5):
            try:
                send_btn = await page.query_selector("button[aria-label='Send message']")
                if send_btn:
                    log(f"🖱 Clicking send button attempt {attempt+1}...")
                    await send_btn.click(force=True)
                    await asyncio.sleep(2)
                    if await page.query_selector("text=Generating") or await page.query_selector("div:has-text('Generating')"):
                        log("✅ Generating detected!")
                        clicked = True
                        break
            except Exception as e:
                log(f"⚠️ Send button issue ({attempt+1}/5): {e}")
            await asyncio.sleep(1)

        if not clicked:
            log("⚠️ Send button might not have triggered, but continuing to wait anyway.")

        # Screenshot AFTER clicking
        after_file = "veo3_after_click.png"
        await page.screenshot(path=after_file)
        upload_screenshot(after_file, "(after clicking send)")

        # Wait for video
        log("⏳ Waiting for video generation (up to 5 min)...")
        video_el = None
        for _ in range(150):
            video_el = await page.query_selector("video") or await page.query_selector("source")
            if video_el:
                break
            await asyncio.sleep(2)

        if not video_el:
            await browser.close()
            raise Exception("❌ No video found after waiting. Check screenshots above.")

        video_url = await video_el.get_attribute("src")
        ext = ".mp4" if ".mp4" in video_url else ".webm"
        raw_file = "veo3_clip" + ext

        log(f"⬇️ Downloading video: {video_url}")
        r = requests.get(video_url, timeout=120)
        with open(raw_file, "wb") as f:
            f.write(r.content)

        log(f"✅ Video ready: {raw_file}")
        await browser.close()
        return raw_file

def upload_instagram_reel(video_path, caption):
    log("📤 Uploading to Instagram...")
    cl = Client()
    try:
        cl.load_settings(SESSION_FILE)
        cl.get_timeline_feed()
        log("✅ Logged in with saved session.")
    except:
        raise Exception("❌ Session invalid, generate a new session.json.")
    cl.clip_upload(video_path, caption)
    log("✅ Reel uploaded successfully!")
    if os.path.exists(video_path):
        os.remove(video_path)
        log(f"🗑 Deleted {video_path}")

async def run_bot():
    log("☑ Starting immediate test post...")
    caption = generate_ai_caption()
    caption += "\n" + generate_ai_hashtags(caption)
    try:
        video = await generate_veo3_video(caption)
        upload_instagram_reel(video, caption)
    except Exception as e:
        log(f"❌ Test post failed: {e}")
        raise SystemExit("Stopping container due to test post failure.")
    log("✅ Test post done. Entering daily schedule...")

if __name__ == "__main__":
    asyncio.run(run_bot())
