# -*- mode: python ; coding: utf-8 -*-

import os
import customtkinter
from PyInstaller.utils.hooks import collect_all

ctk_path = os.path.dirname(customtkinter.__file__)

pydantic_datas, pydantic_binaries, pydantic_hiddenimports = collect_all('pydantic')
pydantic_settings_datas, pydantic_settings_binaries, pydantic_settings_hiddenimports = collect_all('pydantic_settings')

all_datas = [(ctk_path, 'customtkinter'), ('assets', 'assets'), ('src', 'src')] + pydantic_datas + pydantic_settings_datas
all_binaries = pydantic_binaries + pydantic_settings_binaries
all_hiddenimports = [
    'pydantic',
    'pydantic_settings',
    'pydantic_core',
    'pydantic.deprecated.decorator',
    'pydantic.deprecated.tools',
    'zxcvbn',
    'argon2',
    'cryptography',
] + pydantic_hiddenimports + pydantic_settings_hiddenimports

a = Analysis(
    ['src/gui/app.py'],
    pathex=[],
    binaries=all_binaries,
    datas=all_datas,
    hiddenimports=all_hiddenimports,
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
    name='Seednox-Windows-v1.0.3',
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
    icon='assets/app.ico',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Seednox-Windows-v1.0.3',
)
