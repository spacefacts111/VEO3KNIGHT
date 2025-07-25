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
    print(f"{datetime.now().strftime('%H:%M:%S')} - {msg}")

def check_env():
    missing = []
    if not USERNAME: missing.append("IG_USERNAME")
    if not PASSWORD: missing.append("IG_PASSWORD")
    if not GOOGLE_API_KEY: missing.append("GOOGLE_API_KEY")
    if missing:
        raise Exception(f"❌ Missing required environment variables: {', '.join(missing)}")

def check_gemini_cookies():
    log("Checking Gemini cookies...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        if os.path.exists(COOKIES_FILE):
            context.add_cookies(json.load(open(COOKIES_FILE)))
        page = context.new_page()
        page.goto("https://gemini.google.com/app/veo")
        time.sleep(5)
        if "accounts.google.com" in page.url:
            browser.close()
            raise Exception("❌ Cookies invalid or expired. Please regenerate cookies.json.")
        browser.close()
        log("✅ Cookies valid and logged in.")

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
    log(f"🎬 Generating Veo3 video (Attempt {attempt}) for: {prompt}")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        if os.path.exists(COOKIES_FILE):
            context.add_cookies(json.load(open(COOKIES_FILE)))
        page = context.new_page()
        page.goto("https://gemini.google.com/app/veo")

        for _ in range(60):
            if page.query_selector("textarea") or page.query_selector("div[contenteditable='true']"):
                break
            time.sleep(1)

        typed = False
        for _ in range(40):
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
            page.screenshot(path="veo3_error_screenshot.png")
            browser.close()
            if attempt == 1:
                log("⚠️ Typing failed, retrying...")
                return generate_veo3_video(prompt, attempt=2)
            raise Exception("❌ Could not type in the prompt field.")

        page.keyboard.press("Enter")
        log("⏳ Waiting for video generation (up to 5 min)...")

        video_el = None
        for _ in range(150):
            video_el = page.query_selector("video") or page.query_selector("source")
            if video_el:
                break
            time.sleep(2)
        if not video_el:
            page.screenshot(path="veo3_error_screenshot.png")
            browser.close()
            if attempt == 1:
                log("⚠️ Video not found, retrying...")
                return generate_veo3_video(prompt, attempt=2)
            raise Exception("❌ No video found after waiting.")

        video_url = video_el.get_attribute("src")
        ext = ".mp4" if ".mp4" in video_url else ".webm"
        raw_file = "veo3_clip" + ext

        log(f"⬇️ Downloading video: {video_url}")
        try:
            r = requests.get(video_url, timeout=120)
            with open(raw_file, "wb") as f:
                f.write(r.content)
        except:
            if attempt == 1:
                log("⚠️ Download failed, retrying...")
                return generate_veo3_video(prompt, attempt=2)
            raise Exception("❌ Failed to download video.")

        log(f"✅ Video ready: {raw_file}")
        browser.close()
        return raw_file

def upload_instagram_reel(video_path, caption):
    log("📤 Uploading to Instagram...")
    cl = Client()
    if os.path.exists(SESSION_FILE):
        try:
            cl.load_settings(SESSION_FILE)
            cl.get_timeline_feed()
            log("✅ Logged in with saved session.")
        except:
            os.remove(SESSION_FILE)
            raise Exception("❌ Session invalid. Generate a new session.json.")
    else:
        raise Exception("❌ No session.json found. Generate it first.")

    cl.clip_upload(video_path, caption)
    log("✅ Reel uploaded successfully!")
    if os.path.exists(video_path):
        os.remove(video_path)
        log(f"🗑 Deleted {video_path}")

def can_post_now():
    if not os.path.exists(LOCK_FILE):
        return True
    try:
        with open(LOCK_FILE, "r") as f:
            last_time = datetime.fromisoformat(json.load(f).get("last_post"))
        return datetime.now() - last_time > timedelta(hours=6)
    except:
        return True

def update_last_post_time():
    with open(LOCK_FILE, "w") as f:
        json.dump({"last_post": datetime.now().isoformat()}, f)

def run_bot():
    log("☑ Starting bot...")
    check_env()
    check_gemini_cookies()

    # Immediate Test Post
    log("☑ Starting immediate test post...")
    caption = generate_ai_caption()
    caption += "\n" + generate_ai_hashtags(caption)
    try:
        video = generate_veo3_video(caption)
        upload_instagram_reel(video, caption)
        update_last_post_time()
    except Exception as e:
        log(f"❌ Test post failed: {e}")

    log("⏳ Starting daily schedule...")
    while True:
        posts_today = random.randint(1, 2)
        post_times = sorted([
            datetime.now() + timedelta(hours=random.randint(1, 12))
            for _ in range(posts_today)
        ])
        for t in post_times:
            wait = (t - datetime.now()).total_seconds()
            if wait > 0:
                log(f"⏳ Waiting until {t.strftime('%H:%M:%S')} for next post...")
                time.sleep(wait)
            caption = generate_ai_caption()
            caption += "\n" + generate_ai_hashtags(caption)
            try:
                video = generate_veo3_video(caption)
                upload_instagram_reel(video, caption)
                update_last_post_time()
            except Exception as e:
                log(f"❌ Post failed: {e}")
        log("✅ Finished today's posts. Waiting for tomorrow...")
        time.sleep(86400)

if __name__ == "__main__":
    run_bot()
