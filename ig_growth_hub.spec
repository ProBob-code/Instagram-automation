# -*- mode: python ; coding: utf-8 -*-
"""
IG Growth Hub - PyInstaller Spec File
Build with: pyinstaller ig_growth_hub.spec
"""

import os
import sys
from pathlib import Path

block_cipher = None

# Get the directory containing this spec file
SPEC_DIR = os.path.dirname(os.path.abspath(SPECPATH))

# Define data files to include
datas = [
    # Frontend files
    (os.path.join(SPEC_DIR, 'frontend'), 'frontend'),
    # Data directory structure (empty)
    (os.path.join(SPEC_DIR, 'data', 'target_hashtags.txt'), os.path.join('data')),
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
]

a = Analysis(
    ['desktop_app.py'],
    pathex=[SPEC_DIR],
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
