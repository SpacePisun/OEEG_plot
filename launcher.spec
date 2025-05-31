# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_all, copy_metadata, collect_data_files

binaries = []
block_cipher = None

# Собираем метаданные для typing_extensions
typing_extensions_deps = copy_metadata("typing_extensions")

# Основные файлы и папки вашего приложения
datas = [
    ('main.py', '.'),
    ('sidebar.py', '.'),
    ('requirements.txt', '.'),
    ('pages', 'pages'),
    ('.streamlit', '.streamlit'),
]

hiddenimports = ['streamlit.web.bootstrap']

# Добавляем всё, что нужно для streamlit
tmp_ret = collect_all('streamlit')
datas           += tmp_ret[0]
binaries        += tmp_ret[1]
hiddenimports   += tmp_ret[2]

# Вливаем метаданные typing_extensions и файлы plotly и narwhals в datas
datas += typing_extensions_deps
datas += collect_data_files('plotly', include_py_files=True)
datas += collect_data_files('narwhals', include_py_files=True)

a = Analysis(
    ['launcher.py'],          # главный скрипт
    pathex=[os.getcwd()],     # путь к проекту
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
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
    [],                     # доп. файлы, если нужны
    exclude_binaries=True,  # важно для корректной сборки
    name='dist10',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='launcher',
)
