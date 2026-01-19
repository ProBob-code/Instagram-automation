# -*- mode: python ; coding: utf-8 -*-
"""
IG Growth Hub - PyInstaller Spec File
Build with: python -m PyInstaller ig_growth_hub.spec
"""

import os

block_cipher = None

# Use absolute path to project directory
PROJECT_DIR = r'C:\Users\bajacob\.gemini\antigravity\scratch\Instagram automation builder'

# Define data files to include
datas = [
    # Frontend files
    (os.path.join(PROJECT_DIR, 'frontend'), 'frontend'),
    # Data directory structure
    (os.path.join(PROJECT_DIR, 'data'), 'data'),
    # Source code
    (os.path.join(PROJECT_DIR, 'src'), 'src'),
]

# Hidden imports that PyInstaller might miss
hidden_imports = [
    'flask',
    'flask_cors',
    'playwright',
    'playwright.async_api',
    'playwright._impl',
    'playwright._impl._driver',
    'sqlalchemy',
    'werkzeug',
    'aiohttp',
    'httpx',
    'h11',
    'asyncio',
    'concurrent.futures',
    'groq',
    'rich',
    'click',
    'waitress',
]

a = Analysis(
    [os.path.join(PROJECT_DIR, 'desktop_app.py')],
    pathex=[PROJECT_DIR],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'tkinter',
        'PIL',
        'cv2',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='IG_Growth_Hub',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # Set to False for no console window (after testing)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Add icon path here: 'assets/icon.ico'
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='IG_Growth_Hub',
)
