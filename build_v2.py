import PyInstaller.__main__
import customtkinter
import tkcalendar
import babel
import os

ctk_path = customtkinter.__path__[0]
cal_path = tkcalendar.__path__[0]
babel_path = babel.__path__[0]

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

if os.path.exists("app_icon.icns"):
    args.append('--icon=app_icon.icns')

print("🚀 Starting Build Process...")
PyInstaller.__main__.run(args)
print("✅ Build Complete!")