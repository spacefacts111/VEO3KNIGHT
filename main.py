import os
import time
import random
import json
import requests
from datetime import datetime, timedelta
from instagrapi import Client
from playwright.sync_api import sync_playwright

SESSION_FILE = "session.json"
LOCK_FILE = "last_post.json"
COOKIES_FILE = "cookies.json"
USERNAME = os.getenv("IG_USERNAME")
PASSWORD = os.getenv("IG_PASSWORD")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

def log(msg):
    print(f"{datetime.now().strftime('%H:%M:%S')} - {msg}", flush=True)

log("🚀 Bot starting... Performing fail-fast checks.")

# Fail-fast early checks
missing = []
if not USERNAME: missing.append("IG_USERNAME")
if not PASSWORD: missing.append("IG_PASSWORD")
if not GOOGLE_API_KEY: missing.append("GOOGLE_API_KEY")
if not os.path.exists(SESSION_FILE): missing.append("session.json file")
if not os.path.exists(COOKIES_FILE): missing.append("cookies.json file")

if missing:
    log(f"❌ Missing critical requirements: {', '.join(missing)}")
    raise SystemExit("Stopping container due to missing requirements.")

log("✅ All environment variables and files present. Continuing...")

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

def generate_veo3_video(prompt, attempt=1):
    log(f"🎬 Starting Veo3 video generation for: {prompt}")
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True)
        except Exception as e:
            log(f"❌ Failed to start Chromium: {e}")
            raise SystemExit("Stopping container due to Playwright failure.")
        context = browser.new_context()
        context.add_cookies(json.load(open(COOKIES_FILE)))
        page = context.new_page()
        log("⏳ Loading Veo 3 page...")
        page.goto("https://gemini.google.com/app/veo")

        for i in range(60):
            if page.query_selector("textarea") or page.query_selector("div[contenteditable='true']"):
                break
            time.sleep(1)
            log(f"⌛ Waiting for prompt field... {i+1}s")

        typed = False
        for i in range(40):
            try:
                target = page.query_selector("textarea") or page.query_selector("div[contenteditable='true']")
                if target:
                    target.click()
                    page.keyboard.type(prompt, delay=50)
                    typed = True
                    break
            except:
                time.sleep(1)
        if not typed:
            log("❌ Failed to type in Veo 3 prompt field.")
            raise Exception("Could not type in the prompt field.")

        log("🤖 Checking if Veo 3 is already generating...")
        try:
                    # Check if generation is already in progress
                generating = page.query_selector("text=Generating") or page.query_selector("div:has-text('Generating')")
                if generating:
                        log("🔴 Already generating, skipping Submit click.")
                        gen_btn = None
                else:
                        log("🖱 Clicking the Submit button...")
                        gen_btn = (
                page.query_selector("button:has-text('Submit')") or 
                page.query_selector("button:has-text('Generate')") or 
                page.query_selector("button")
            )
            if gen_btn:
                gen_btn.click()
                    else:
                log("⚠️ No Generate button found, pressing Enter as fallback.")
                page.keyboard.press("Enter")
        except:
            log("⚠️ Failed to click, pressing Enter instead.")
            page.keyboard.press("Enter")
        log("⏳ Waiting for video generation (up to 5 min)...")

        video_el = None
        for i in range(150):
            video_el = page.query_selector("video") or page.query_selector("source")
            if video_el:
                break
            time.sleep(2)
            if i % 10 == 0:
                log(f"⌛ Still waiting for video... {i*2}s")
        if not video_el:
            log("❌ No video found after waiting.")
            browser.close()
            if attempt == 1:
                log("🔄 Refreshing page and retrying video generation...")
                log('🔄 Retrying video generation now...')
                return generate_veo3_video(prompt, attempt=2)
            raise Exception("No video found after retry.")

        video_url = video_el.get_attribute("src")
        ext = ".mp4" if ".mp4" in video_url else ".webm"
        raw_file = "veo3_clip" + ext

        log(f"⬇️ Downloading video: {video_url}")
        r = requests.get(video_url, timeout=120)
        with open(raw_file, "wb") as f:
            f.write(r.content)

        log(f"✅ Video ready: {raw_file}")
        browser.close()
        return raw_file

def upload_instagram_reel(video_path, caption):
    log("📤 Uploading to Instagram...")
    cl = Client()
    try:
        cl.load_settings(SESSION_FILE)
        cl.get_timeline_feed()
        log("✅ Logged in with saved session.")
    except:
        log("❌ Session invalid, stopping.")
        raise SystemExit("Stopping container due to invalid session.")

    cl.clip_upload(video_path, caption)
    log("✅ Reel uploaded successfully!")
    if os.path.exists(video_path):
        os.remove(video_path)
        log(f"🗑 Deleted {video_path}")

def run_bot():
    log("☑ Starting immediate test post...")
    caption = generate_ai_caption()
    caption += "\n" + generate_ai_hashtags(caption)
    try:
        video = generate_veo3_video(caption)
        upload_instagram_reel(video, caption)
    except Exception as e:
        log(f"❌ Test post failed: {e}")
        raise SystemExit("Stopping container due to test post failure.")
    log("✅ Test post done. Entering daily schedule...")

if __name__ == "__main__":
    run_bot()
