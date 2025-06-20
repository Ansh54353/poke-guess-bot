import os
import json
import asyncio
from datetime import datetime, timedelta
from PIL import Image
import imagehash
from telethon import TelegramClient, events

# === CONFIG ===
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
SESSION_NAME = "session"
MAIN_GROUP = -1002703086057
LOG_GROUP = -1002684463909
HASH_DB_FILE = "hash_db.json"
IMAGE_FOLDER = "shadow_images"
os.makedirs(IMAGE_FOLDER, exist_ok=True)

# === STATE ===
known_hashes = {}
hash_waitlist = {}  # msg_id: hash_id
last_hash = None
learned = 0

# === LOAD DB ===
if os.path.exists(HASH_DB_FILE):
    with open(HASH_DB_FILE, 'r') as f:
        known_hashes = json.load(f)

# === INIT CLIENT ===
client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

# === IMAGE HASHING ===
def get_hash(path):
    try:
        img = Image.open(path)
        return str(imagehash.average_hash(img))
    except Exception as e:
        return None

# === HANDLE IMAGE ===
@client.on(events.NewMessage(chats=MAIN_GROUP))
async def on_image(event):
    global last_hash
    if event.photo:
        path = await event.download_media(file=IMAGE_FOLDER)
        hash_id = get_hash(path)
        if hash_id and hash_id not in known_hashes:
            last_hash = hash_id
            await client.send_message(LOG_GROUP, f"🧩 Image seen → Hash: `{hash_id}`")

# === HANDLE NAME REVEAL ===
@client.on(events.NewMessage(chats=MAIN_GROUP))
async def on_reveal(event):
    global learned, last_hash

    lines = event.raw_text.lower().splitlines()
    for line in lines:
        if "the pokemon was" in line:
            name = line.split("was")[-1].strip().lower()
            if last_hash and last_hash not in known_hashes:
                known_hashes[last_hash] = name
                with open(HASH_DB_FILE, 'w') as f:
                    json.dump(known_hashes, f, indent=2)

                await client.send_message(LOG_GROUP, f"✅ Learned → `{last_hash}` : `{name}`")
                learned += 1

                if learned % 50 == 0:
                    await client.send_file(LOG_GROUP, HASH_DB_FILE, caption=f"📦 Auto-sent after {learned} learns.")

                last_hash = None

# === CLEAN SHUTDOWN ===
async def shutdown():
    await client.send_message(LOG_GROUP, "⏹️ Bot shutting down. Sending final DB...")
    await client.send_file(LOG_GROUP, HASH_DB_FILE, caption=f"📦 Final DB ({len(known_hashes)} entries)")

import signal
import sys
def handler(sig, frame):
    asyncio.get_event_loop().create_task(shutdown())
    sys.exit(0)
signal.signal(signal.SIGINT, handler)
signal.signal(signal.SIGTERM, handler)

# === START ===
client.start()
print("🚀 Bot started.")
client.run_until_disconnected()
