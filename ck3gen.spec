# ck3gen.spec

# 1. Add this import at the top
from PyInstaller.utils.hooks import collect_all

block_cipher = None

# 2. Collect everything related to streamlit
streamlit_data = collect_all('streamlit')
matplotlib_data = collect_all('matplotlib')
graphviz_data = collect_all('graphviz')

# 3. Construct the Analysis with injected metadata + collected files
a = Analysis(
    ['launcher.py'],
    pathex=[],
    binaries=streamlit_data[1] + matplotlib_data[1] + graphviz_data[1],
    datas=[
        ('main.py', '.'),  # ✅ tuple form
        ('interface/ui_app.py', 'interface'),
        ('utils/utils.py', 'utils'),
        ('ck3gen/character.py', 'ck3gen'),
        ('ck3gen/config_loader.py', 'ck3gen'),
        ('ck3gen/dynasty_creation.py', 'ck3gen'),
        ('ck3gen/family_tree.py', 'ck3gen'),
        ('ck3gen/name_loader.py', 'ck3gen'),
        ('ck3gen/simulation.py', 'ck3gen'),
        ('ck3gen/title_history.py', 'ck3gen'),
        ('config/*.json', 'config'),
        ('config/fallback_config_files/*.json', 'config/fallback_config_files'),
        *streamlit_data[0],
        *matplotlib_data[0],
        *graphviz_data[0],
    ],
    hiddenimports=list(set(
        streamlit_data[2] + matplotlib_data[2] + graphviz_data[2] + [
            'streamlit',
            'streamlit.components.v1',
            'streamlit.server',
            'streamlit.server.server',
            'matplotlib.pyplot',
            'graphviz'
        ]
    )),
    hookspath=[],
    runtime_hooks=[],
    excludes=['streamlit.external.langchain'],  # <== Correct placement
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
    debug=True,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True  # Set to True to see terminal output on crash
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
