# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['GameEditor.py'],
    pathex=[],
    binaries=[],
    datas=[('E:\\2DGameEditor\\Assets', 'Assets')],
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
    a.binaries,
    a.datas,
    [],
    name='2DGameEditor_v2.1.1',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir='%LOCALAPPDATA%\\2DGameEditor',
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version='dist\\version_info.txt',
    icon=['E:\\2DGameEditor\\Assets\\EditorIcon.ico'],
)
