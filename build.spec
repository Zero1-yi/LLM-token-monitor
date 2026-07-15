# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec file for LLM Token Monitor.

Build command:
    pyinstaller build.spec --clean --noconfirm

Output: dist/LLMTokenMonitor.exe (single-file, no console window)
"""

import sys
from pathlib import Path

# Ensure the project root is on the path so imports resolve
_PROJECT_ROOT = Path(SPECPATH)
sys.path.insert(0, str(_PROJECT_ROOT))

# Collect all DLLs from Python's DLLs/ and Library/bin/ directories
# Fixes _ctypes → ffi.dll dependency chain on conda Python
import os as _os
import sys as _sys
_binaries = []
for _dir in (
    _os.path.join(_sys.prefix, 'DLLs'),
    _os.path.join(_sys.prefix, 'Library', 'bin'),
):
    if _os.path.isdir(_dir):
        for _f in _os.listdir(_dir):
            if _f.endswith(('.pyd', '.dll')):
                _binaries.append((_os.path.join(_dir, _f), '.'))

a = Analysis(
    ['main.py'],
    pathex=[str(_PROJECT_ROOT)],
    binaries=_binaries,
    datas=[],
    hiddenimports=[
        '_ctypes',
        'pystray._win32',
        'pystray._util',
        'PIL._imagingft',
        'cryptography.hazmat.backends.openssl',
        'cryptography.hazmat.primitives.ciphers',
        'cryptography.hazmat.primitives.hashes',
        'tkinter',
        'tkinter.ttk',
        'tkinter.messagebox',
        'tkinter.filedialog',
        'httpx',
        'httpcore',
        'h11',
        'certifi',
        'idna',
        'i18n',
        'providers',
        'providers.base',
        'providers.openai_provider',
        'providers.deepseek_provider',
        'ssl',
        'certifi',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'tensorflow',
        'torch',
        'jupyter',
        'IPython',
        'pytest',
        'setuptools',
        'pip',
        'wheel',
        'tkinter.test',
        'unittest',
        'test',
        'tests',
        'xml.etree',
        'lib2to3',
        'multiprocessing',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='LLMTokenMonitor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # No console window — pure tray/UI app
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(_PROJECT_ROOT / 'icon.ico') if (_PROJECT_ROOT / 'icon.ico').exists() else None,
)
