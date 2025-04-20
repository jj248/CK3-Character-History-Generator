# ck3gen.spec

block_cipher = None

a = Analysis(
    ['interface/ui_app.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('config/*.json', 'config'),
        ('config/fallback_config_files/*.json', 'config/fallback_config_files')
    ],
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='CK3CharacterGenerator',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False  # Set to True if you want a terminal window too
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='CK3CharacterGenerator'
)
