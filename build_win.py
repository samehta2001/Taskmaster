import PyInstaller.__main__
import customtkinter
import tkcalendar
import babel
import os
import sys
from PIL import Image # Requires: pip install Pillow

# --- CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
APP_NAME = "TaskMaster"
MAIN_SCRIPT = os.path.join(BASE_DIR, "taskmaster.py")
ICON_PNG = os.path.join(BASE_DIR, "logo.png")
ICON_ICO = os.path.join(BASE_DIR, "icon.ico")

# --- 1. GENERATE WINDOWS ICON (.ICO) ---
def create_ico():
    if not os.path.exists(ICON_PNG):
        print(f"⚠️ Warning: {ICON_PNG} not found. Using default icon.")
        return False
    
    print("🎨 Converting PNG to ICO...")
    try:
        img = Image.open(ICON_PNG)
        # Windows icons need specific sizes embedded
        img.save(ICON_ICO, format='ICO', sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
        print("✅ Icon created.")
        return True
    except Exception as e:
        print(f"❌ Icon creation failed: {e}")
        return False

# --- 2. BUILD THE EXE ---
def build_app():
    has_icon = create_ico()

    ctk_path = customtkinter.__path__[0]
    cal_path = tkcalendar.__path__[0]
    babel_path = babel.__path__[0]

    # Windows uses ';' separator for add-data
    # Mac/Linux uses ':'
    sep = ';' 

    args = [
        MAIN_SCRIPT,
        f'--name={APP_NAME}',
        '--noconsole',
        '--clean',
        '--noconfirm',
        '--onefile', # Creates a single .exe file (easier to share)
        
        # Add Data (Note the 'sep' variable)
        f'--add-data={ctk_path}{sep}customtkinter',
        f'--add-data={cal_path}{sep}tkcalendar',
        f'--add-data={babel_path}{sep}babel',
    ]

    if has_icon:
        args.append(f'--icon={ICON_ICO}')

    print("🔨 Starting PyInstaller Build (Windows)...")
    PyInstaller.__main__.run(args)
    print("✅ Build Complete! Check the 'dist' folder.")

if __name__ == "__main__":
    build_app()