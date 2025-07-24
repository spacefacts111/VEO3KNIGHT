import os
import time
import random
import json
from datetime import datetime, timedelta
from instagrapi import Client
from google import genai

# ===== CONFIG =====
SESSION_FILE = "session.json"
LOCK_FILE = "last_post.json"
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
USERNAME = os.getenv("IG_USERNAME")
PASSWORD = os.getenv("IG_PASSWORD")
client = genai.Client(api_key=GOOGLE_API_KEY)

# ===== HASHTAGS =====
HASHTAGS = [
    "#sad", "#brokenhearts", "#nightvibes", "#relatable", "#heartbroken",
    "#viral", "#fyp", "#explorepage", "#love", "#deepthoughts",
    "#depressedquotes", "#darkquotes", "#poetry", "#trending"
]

PROMPTS = [
    "A lonely boy walking through neon-lit rainy streets, cinematic mood",
    "A girl staring at the city lights from a rooftop, melancholy vibe",
    "Slow motion raindrops on a window with blurred city lights",
    "A lone figure walking under street lamps on a foggy night, artistic",
    "A couple sitting apart on a bench under the rain, poetic atmosphere"
]

CAPTIONS = [
    "Some things hurt more in silence.",
    "I break in places no one can see.",
    "Rain hides my tears but not my pain.",
    "We stopped talking, but I still hear you.",
    "I hope you think of me when it’s quiet."
]

def mix_hashtags():
    selected = random.sample(HASHTAGS, 6)
    return " ".join(selected)

# ===== VEO 3 VIDEO GENERATION =====
def generate_veo3_video(prompt):
    print(f"🎬 Generating Veo3 Fast video for: {prompt}")
    operation = client.models.generate_videos(
        model="veo-3.0-generate-preview",
        prompt=prompt,
        config=genai.types.GenerateVideosConfig(
            resolution="1080p",
            generateAudio=True,
            sampleCount=1
        )
    )
    while not operation.done:
        time.sleep(10)
        operation = client.operations.get(operation)

    generated = operation.response.generated_videos[0]
    filename = "veo3_clip.mp4"
    client.files.download(file=generated.video)
    generated.video.save(filename)
    print(f"✅ Video saved: {filename}")
    return filename

# ===== INSTAGRAM UPLOAD =====
def upload_instagram_reel(video_path, caption):
    print("📤 Uploading to Instagram...")
    cl = Client()

    if os.path.exists(SESSION_FILE):
        try:
            cl.load_settings(SESSION_FILE)
            cl.get_timeline_feed()
            print("✅ Logged in with saved session.")
        except:
            print("⚠️ Session corrupted, regenerating...")
            os.remove(SESSION_FILE)

    if not os.path.exists(SESSION_FILE):
        cl.login(USERNAME, PASSWORD)
        cl.dump_settings(SESSION_FILE)
        print("✅ New session saved.")

    try:
        cl.clip_upload(video_path, caption)
        print("✅ Reel uploaded successfully!")
    except Exception as e:
        print(f"❌ Upload failed: {e}")

# ===== LOCK SYSTEM =====
def can_post_now():
    if not os.path.exists(LOCK_FILE):
        return True
    try:
        with open(LOCK_FILE, "r") as f:
            data = json.load(f)
        last_time = datetime.fromisoformat(data.get("last_post"))
        if datetime.now() - last_time > timedelta(hours=6):
            return True
        return False
    except:
        return True

def update_last_post_time():
    with open(LOCK_FILE, "w") as f:
        json.dump({"last_post": datetime.now().isoformat()}, f)

# ===== AUTOMATED LOOP =====
def run_bot():
    # Immediate post if allowed
    if can_post_now():
        caption = random.choice(CAPTIONS) + "\n" + mix_hashtags()
        video = generate_veo3_video(random.choice(PROMPTS))
        upload_instagram_reel(video, caption)
        update_last_post_time()

    print("⏳ Starting daily schedule...")
    while True:
        # Schedule 1-3 posts per day
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

            caption = random.choice(CAPTIONS) + "\n" + mix_hashtags()
            video = generate_veo3_video(random.choice(PROMPTS))
            upload_instagram_reel(video, caption)
            update_last_post_time()

        print("✅ Finished today's posts. Waiting for tomorrow...")
        time.sleep(86400)  # wait 24 hours

if __name__ == "__main__":
    run_bot()
