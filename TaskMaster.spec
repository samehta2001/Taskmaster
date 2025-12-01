# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['/Users/sameer.mehta/Library/CloudStorage/OneDrive-RelianceCorporateITParkLimited/Projects/AI Coding/ToDoer/TaskMaster/taskmaster.py'],
    pathex=[],
    binaries=[],
    datas=[('/Users/sameer.mehta/Library/CloudStorage/OneDrive-RelianceCorporateITParkLimited/Projects/AI Coding/ToDoer/venv/lib/python3.14/site-packages/customtkinter', 'customtkinter'), ('/Users/sameer.mehta/Library/CloudStorage/OneDrive-RelianceCorporateITParkLimited/Projects/AI Coding/ToDoer/venv/lib/python3.14/site-packages/tkcalendar', 'tkcalendar'), ('/Users/sameer.mehta/Library/CloudStorage/OneDrive-RelianceCorporateITParkLimited/Projects/AI Coding/ToDoer/venv/lib/python3.14/site-packages/babel', 'babel')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='TaskMaster',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['/Users/sameer.mehta/Library/CloudStorage/OneDrive-RelianceCorporateITParkLimited/Projects/AI Coding/ToDoer/TaskMaster/app_icon.icns'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='TaskMaster',
)
app = BUNDLE(
    coll,
    name='TaskMaster.app',
    icon='/Users/sameer.mehta/Library/CloudStorage/OneDrive-RelianceCorporateITParkLimited/Projects/AI Coding/ToDoer/TaskMaster/app_icon.icns',
    bundle_identifier=None,
)
