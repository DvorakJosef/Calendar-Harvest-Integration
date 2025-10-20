# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Calendar Harvest Integration Desktop App
Build command: pyinstaller desktop_app.spec
"""

import sys
from pathlib import Path

block_cipher = None

# Get the project root directory
project_root = Path(__file__).parent

a = Analysis(
    ['desktop_app.py'],
    pathex=[str(project_root)],
    binaries=[],
    datas=[
        ('templates', 'templates'),
        ('static', 'static'),
        ('.env.development', '.'),
        ('.env.example', '.'),
    ],
    hiddenimports=[
        'flask',
        'flask_sqlalchemy',
        'flask_wtf',
        'flask_limiter',
        'flask_talisman',
        'google.auth',
        'google.auth.oauthlib',
        'google.auth.transport.requests',
        'google.oauth2.service_account',
        'google.api_core',
        'googleapiclient.discovery',
        'requests',
        'requests_oauthlib',
        'dotenv',
        'webview',
        'marshmallow',
        'sqlalchemy',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludedimports=[
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Calendar Harvest Integration',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='static/icon.icns',
)

app = BUNDLE(
    exe,
    name='Calendar Harvest Integration.app',
    icon='static/icon.icns',
    bundle_identifier='com.calendar-harvest.integration',
    info_plist={
        'NSPrincipalClass': 'NSApplication',
        'NSHighResolutionCapable': 'True',
        'NSRequiresIPhoneOS': False,
        'LSMinimumSystemVersion': '10.13.0',
        'NSHumanReadableCopyright': 'Copyright 2025. All rights reserved.',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
    },
    pkg_resources=[],
    strip=False,
    upx=True,
)

