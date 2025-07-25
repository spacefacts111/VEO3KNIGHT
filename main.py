
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

def check_gemini_cookies():
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
        print("✅ Cookies valid and logged in.")

def generate_ai_caption():
    prompt = (
        "Write a short, hard-hitting, sad or metaphorical quote that feels viral and relatable. "
        "Mix 60% heartbreak truths, 30% poetic metaphors, 10% thought-provoking questions. "
        "Max 15 words."
    )
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GOOGLE_API_KEY}"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    r = requests.post(url, json=payload)
    if r.status_code == 200:
        return r.json()["candidates"][0]["content"]["parts"][0]["text"]
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
    r = requests.post(url, json=payload)
    if r.status_code == 200:
        return r.json()["candidates"][0]["content"]["parts"][0]["text"]
    return "#sad #brokenhearts #viral #fyp #poetry"

def generate_veo3_video(prompt):
    print(f"🎬 Generating Veo3 video for: {prompt}")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        if os.path.exists(COOKIES_FILE):
            context.add_cookies(json.load(open(COOKIES_FILE)))
        page = context.new_page()
        page.goto("https://gemini.google.com/app/veo")

        print("⏳ Waiting for prompt input field...")
        for i in range(60):
            if page.query_selector("textarea") or page.query_selector("div[contenteditable='true']"):
                break
            time.sleep(1)

        if page.query_selector("textarea"):
            page.fill("textarea", prompt)
        elif page.query_selector("div[contenteditable='true']"):
            page.fill("div[contenteditable='true']", prompt)
        else:
            raise Exception("❌ Could not find a prompt input field.")

        page.keyboard.press("Enter")
        print("⏳ Waiting for video generation...")

        for i in range(120):
            video_el = page.query_selector("video")
            if video_el:
                break
            time.sleep(2)

        video_el = page.query_selector("video")
        if not video_el:
            raise Exception("❌ Video generation failed (no video element found).")

        video_url = video_el.get_attribute("src")
        filename = "veo3_clip.mp4"
        r = requests.get(video_url)
        with open(filename, "wb") as f:
            f.write(r.content)
        print(f"✅ Video saved: {filename}")

        browser.close()
        return filename

def upload_instagram_reel(video_path, caption):
    print("📤 Uploading to Instagram...")
    cl = Client()
    if os.path.exists(SESSION_FILE):
        try:
            cl.load_settings(SESSION_FILE)
            cl.get_timeline_feed()
            print("✅ Logged in with saved session.")
        except:
            os.remove(SESSION_FILE)
            print("⚠️ Session corrupted, regenerating...")
    if not os.path.exists(SESSION_FILE):
        cl.login(USERNAME, PASSWORD)
        cl.dump_settings(SESSION_FILE)
        print("✅ New session saved.")
    cl.clip_upload(video_path, caption)
    print("✅ Reel uploaded successfully!")
    if os.path.exists(video_path):
        os.remove(video_path)
        print(f"🗑 Deleted {video_path} to save space.")

def can_post_now():
    if not os.path.exists(LOCK_FILE):
        return True
    try:
        with open(LOCK_FILE, "r") as f:
            data = json.load(f)
        last_time = datetime.fromisoformat(data.get("last_post"))
        return datetime.now() - last_time > timedelta(hours=6)
    except:
        return True

def update_last_post_time():
    with open(LOCK_FILE, "w") as f:
        json.dump({"last_post": datetime.now().isoformat()}, f)

def run_bot():
    check_gemini_cookies()
    if can_post_now():
        caption = generate_ai_caption()
        caption += "\n" + generate_ai_hashtags(caption)
        video = generate_veo3_video(caption)
        upload_instagram_reel(video, caption)
        update_last_post_time()
    print("⏳ Starting daily schedule...")
    while True:
        posts_today = random.randint(1, 3)
        post_times = sorted([
            datetime.now() + timedelta(hours=random.randint(1, 12))
            for _ in range(posts_today)
        ])
        for t in post_times:
            wait = (t - datetime.now()).total_seconds()
            if wait > 0:
                print(f"⏳ Waiting until {t.strftime('%H:%M:%S')} for next post...")
                time.sleep(wait)
            caption = generate_ai_caption()
            caption += "\n" + generate_ai_hashtags(caption)
            video = generate_veo3_video(caption)
            upload_instagram_reel(video, caption)
            update_last_post_time()
        print("✅ Finished today's posts. Waiting for tomorrow...")
        time.sleep(86400)

if __name__ == "__main__":
    run_bot()
