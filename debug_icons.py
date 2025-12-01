import os
import shutil
import json

# Setup Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
JSON_FILE = os.path.join(ASSETS_DIR, "icons.json")
ICONSET_DIR = os.path.join(BASE_DIR, "app_icon.iconset")

# 1. Clean and Create Folder
if os.path.exists(ICONSET_DIR): shutil.rmtree(ICONSET_DIR)
os.makedirs(ICONSET_DIR)

# 2. Strict Whitelist (macOS allows ONLY these)
VALID_NAMES = {
    "icon_16x16.png", "icon_16x16@2x.png",
    "icon_32x32.png", "icon_32x32@2x.png",
    "icon_128x128.png", "icon_128x128@2x.png",
    "icon_256x256.png", "icon_256x256@2x.png",
    "icon_512x512.png", "icon_512x512@2x.png"
}

# 3. Copy Files
with open(JSON_FILE, 'r') as f:
    data = json.load(f)

print(f"📂 Preparing {ICONSET_DIR}...")

for img_entry in data.get('images', []):
    source_filename = img_entry.get('filename')
    size = img_entry.get('size') 
    scale = img_entry.get('scale') 

    if not source_filename or not size or not scale: continue

    scale_suffix = "" if scale == "1x" else "@2x"
    dest_filename = f"icon_{size}{scale_suffix}.png"
    
    if dest_filename in VALID_NAMES:
        src = os.path.join(ASSETS_DIR, source_filename)
        dst = os.path.join(ICONSET_DIR, dest_filename)
        if os.path.exists(src):
            shutil.copy(src, dst)
            print(f"   -> Copied {dest_filename}")
        else:
            print(f"   ❌ MISSING: {source_filename}")

print("\n✅ Folder ready.")
print("👉 Now run this command in terminal:")
print(f"iconutil -c icns '{ICONSET_DIR}' -o app_icon.icns")