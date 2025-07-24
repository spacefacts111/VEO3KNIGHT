import os
import time
import json
import random
from datetime import datetime, timedelta
from instagrapi import Client
from google.cloud import aiplatform

# ===== CONFIG =====
SESSION_FILE = "session.json"
LOCK_FILE = "last_post.json"
USERNAME = os.getenv("IG_USERNAME")
PASSWORD = os.getenv("IG_PASSWORD")

# ===== SETUP GOOGLE CREDENTIALS =====
# Load JSON from Railway variable
credentials_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
with open("google_credentials.json", "w") as f:
    f.write(credentials_json)
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "google_credentials.json"

aiplatform.init(project=json.loads(credentials_json)["project_id"], location="us-central1")

# ===== HASHTAGS & PROMPTS =====
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
    return " ".join(random.sample(HASHTAGS, 6))

# ===== VEO 3 VIDEO GENERATION (Vertex AI) =====
def generate_veo3_video(prompt):
    print(f"🎬 Generating Veo3 video for: {prompt}")
    model = "veo-3.0-generate-preview"
    operation = aiplatform.gapic.PipelineServiceClient().create_training_pipeline(
        parent=f"projects/{json.loads(credentials_json)['project_id']}/locations/us-central1",
        training_pipeline={
            "display_name": "veo3-video-gen",
            "input_data_config": {},
            "model_to_upload": {
                "display_name": prompt,
                "labels": {}
            }
        }
    )
    # NOTE: Vertex AI actual video gen is different; using placeholder logic due to limitations
    # In real-world, you'd call aiplatform.VideoGenerationModel(...)
    filename = "veo3_clip.mp4"
    open(filename, "wb").write(b"FAKE_VIDEO_CONTENT")  # placeholder
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
        return datetime.now() - last_time > timedelta(hours=6)
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
        time.sleep(86400)

if __name__ == "__main__":
    run_bot()
