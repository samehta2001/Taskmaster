import PyInstaller.__main__
import customtkinter
import tkcalendar
import babel
import os
import subprocess
import shutil

# --- 1. ICON GENERATION FUNCTION ---
def create_icns_from_png(png_path, icns_path):
    """
    Creates a multi-resolution .icns file from a single high-res .png file
    using native macOS tools (sips and iconutil).
    """
    if not os.path.exists(png_path):
        print(f"⚠️  No {png_path} found. Skipping icon creation.")
        return False

    print(f"🎨 Creating {icns_path} from {png_path}...")
    
    iconset_dir = "app_icon.iconset"
    if os.path.exists(iconset_dir):
        shutil.rmtree(iconset_dir)
    os.makedirs(iconset_dir)

    # List of standard icon sizes for macOS
    sizes = [16, 32, 64, 128, 256, 512]
    
    try:
        # Create standard sizes
        for size in sizes:
            subprocess.run(["sips", "-z", str(size), str(size), png_path, 
                            "--out", os.path.join(iconset_dir, f"icon_{size}x{size}.png")], 
                           check=True, stdout=subprocess.DEVNULL)
        
        # Create retina sizes (e.g., 32x32@2x)
        for size in sizes[:-1]: # Skip the largest one for retina
            retina_size = size * 2
            subprocess.run(["sips", "-z", str(retina_size), str(retina_size), png_path, 
                            "--out", os.path.join(iconset_dir, f"icon_{size}x{size}@2x.png")], 
                           check=True, stdout=subprocess.DEVNULL)

        # Create the final .icns file
        subprocess.run(["iconutil", "-c", "icns", iconset_dir, "-o", icns_path], check=True)
        print("✅ Icon created successfully!")
        return True

    except subprocess.CalledProcessError as e:
        print(f"❌ Error creating icon: {e}")
        return False
    finally:
        # Cleanup temporary iconset folder
        if os.path.exists(iconset_dir):
            shutil.rmtree(iconset_dir)


# --- 2. GET LIBRARY PATHS ---
ctk_path = customtkinter.__path__[0]
cal_path = tkcalendar.__path__[0]
babel_path = babel.__path__[0]

# --- 3. DEFINE PYINSTALLER ARGS ---
args = [
    'taskmaster.py',
    '--name=TaskMaster',
    '--windowed',
    '--noconsole',
    '--clean',
    '--noconfirm',
    
    f'--add-data={ctk_path}:customtkinter',
    f'--add-data={cal_path}:tkcalendar',
    f'--add-data={babel_path}:babel',
]

# --- 4. GENERATE AND ADD ICON ---
# Will create app_icon.icns from logo.png if it exists
if create_icns_from_png("logo.png", "app_icon.icns"):
    args.append('--icon=app_icon.icns')

# --- 5. RUN THE BUILD ---
print("🚀 Starting Universal Build...")
PyInstaller.__main__.run(args)
print("✅ Build Complete! Your app is in the 'dist' folder.")