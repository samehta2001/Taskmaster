import PyInstaller.__main__
import customtkinter
import tkcalendar
import babel
import os
import subprocess
import shutil
import sys
import stat

# --- CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
APP_NAME = "TaskMaster"
MAIN_SCRIPT = os.path.join(BASE_DIR, "taskmaster.py")
ICON_ICNS = os.path.join(BASE_DIR, "app_icon.icns")

# --- 1. BUILD THE APP ---
def build_app():
    if not os.path.exists(ICON_ICNS):
        print(f"❌ Error: {ICON_ICNS} not found!")
        return

    print(f"✅ Found Icon: {ICON_ICNS}")

    ctk_path = customtkinter.__path__[0]
    cal_path = tkcalendar.__path__[0]
    babel_path = babel.__path__[0]

    args = [
        MAIN_SCRIPT,
        f'--name={APP_NAME}',
        '--windowed',
        '--noconsole',
        '--clean',
        '--noconfirm',
        f'--add-data={ctk_path}:customtkinter',
        f'--add-data={cal_path}:tkcalendar',
        f'--add-data={babel_path}:babel',
        f'--icon={ICON_ICNS}'
    ]

    print("🔨 Starting PyInstaller Build...")
    PyInstaller.__main__.run(args)
    print("✅ .app Build Complete.")

# --- 2. FIX PERMISSIONS & SIGN (NEW) ---
def fix_permissions_and_sign():
    """
    Forces the binary to be executable and applies ad-hoc signature.
    This prevents 'Permission Denied' errors on new machines.
    """
    dist_dir = os.path.join(BASE_DIR, "dist")
    app_path = os.path.join(dist_dir, f"{APP_NAME}.app")
    
    # 1. Locate the inner binary (TaskMaster.app/Contents/MacOS/TaskMaster)
    binary_path = os.path.join(app_path, "Contents", "MacOS", APP_NAME)
    
    if os.path.exists(binary_path):
        print("🔧 Fixing Permissions...")
        # Equivalent to 'chmod +x'
        st = os.stat(binary_path)
        os.chmod(binary_path, st.st_mode | stat.S_IEXEC)
    
    # 2. Ad-hoc Codesign (Crucial for M1/M2/M3 Macs)
    # This tells macOS the executable is valid, even without a paid ID.
    print("🔏 Applying Ad-Hoc Signature...")
    try:
        subprocess.run(["codesign", "--force", "--deep", "-s", "-", app_path], check=True)
        print("✅ App Signed (Ad-hoc).")
    except Exception as e:
        print(f"⚠️ Warning: Codesign failed ({e}). App might need manual chmod on target.")

# --- 3. CREATE DMG ---
def create_dmg():
    print("📦 Creating DMG Installer...")
    
    if shutil.which("create-dmg") is None:
        print("❌ 'create-dmg' not found. Run: brew install create-dmg")
        return

    dist_dir = os.path.join(BASE_DIR, "dist")
    app_source = os.path.join(dist_dir, f"{APP_NAME}.app")
    dmg_output = os.path.join(dist_dir, f"{APP_NAME}_Installer.dmg")

    if os.path.exists(dmg_output):
        os.remove(dmg_output)

    cmd = [
        "create-dmg",
        "--volname", f"{APP_NAME} Installer",
        "--window-pos", "200", "120",
        "--window-size", "800", "400",
        "--icon-size", "100",
        "--icon", f"{APP_NAME}.app", "200", "190",
        "--hide-extension", f"{APP_NAME}.app",
        "--app-drop-link", "600", "185",
        dmg_output,
        app_source
    ]

    try:
        subprocess.run(cmd, check=True)
        print(f"🎉 Success! DMG created at: {dmg_output}")
    except subprocess.CalledProcessError as e:
        print(f"❌ DMG creation failed: {e}")

if __name__ == "__main__":
    os.chdir(BASE_DIR)
    build_app()
    fix_permissions_and_sign() # <--- Run this before creating DMG
    create_dmg()