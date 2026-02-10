# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

# Inclua apenas os módulos realmente usados
hiddenimports = (
    collect_submodules('automation') +
    collect_submodules('config') +
    collect_submodules('core') +
    collect_submodules('input') +
    collect_submodules('services') +
    collect_submodules('utils') +
    collect_submodules('vision') +
    collect_submodules('gui') +
    [
        'jaraco', 'jaraco.text', 'jaraco.classes', 'jaraco.collections', 'jaraco.functools'
    ]
)

# Inclua recursos essenciais (ajuste se necessário)
import site
import glob

datas = [
    ('release/audio/fruit-notification.mp3', 'audio'),
    ('release/icon.ico', 'release'),
]


# Exclua módulos grandes/desnecessários (including RapidOCR/ONNX Runtime)
excludes = [
        'torch', 'torchvision', 'tensorflow', 'tensorboard',
        'matplotlib', 'scipy', 'pandas', 'IPython', 'jupyter',
        'notebook', 'sphinx', 'pytest', 'test', 'tests',
        'unittest', 'doctest', 'setuptools', 'wheel', 'pip',
        'rapidocr_onnxruntime', 'onnxruntime', 'onnx'
]

# Build otimizada, 1 exe, sem console

a = Analysis(
    ['bps_fishing_macro_v1.0.3.py'],
    pathex=[],
    binaries=[],
    datas=[('config', 'config'), ('gui', 'gui'), ('core', 'core'), ('utils', 'utils'), ('services', 'services'), ('vision', 'vision'), ('automation', 'automation'), ('bpsfishmacrosettings.json', '.'), ('fishing_stats.db', '.')],
    hiddenimports=['PIL._tkinter_finder', 'pynput.keyboard._win32', 'pynput.mouse._win32', 'mss', 'cv2', 'numpy', 'win32gui', 'win32api', 'win32con', 'discord', 'discord.ext.commands'],
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
    name='bps_fishing_macro_v1.0.3',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    console=False,
    icon='release\\icon.ico',
)
