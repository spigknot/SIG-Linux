# -*- mode: python ; coding: utf-8 -*-
# Spec do SIG Linux (PyInstaller one-dir).

import sys
from pathlib import Path

# O Python usado no build (uv) carrega Tcl/Tk 9.0 de libs próprias que não
# existem no sistema (que pode ter só 8.6). Sem elas o executável falha com
# "libtcl9.0.so: cannot open shared object file". Coletamos explicitamente
# as libs do diretório do interpretador para o _internal/ do pacote.
_py_lib_dir = Path(sys.base_prefix) / "lib"
_tcl_tk_binaries = []
for _name in (
    "libtcl9.0.so",
    "libtcl9tk9.0.so",
    "libtcl9thread3.0.4.so",
    "libtcl8.6.so",
    "libtcl8.6.so.0",
    "libtk8.6.so",
    "libtk8.6.so.0",
):
    _candidate = _py_lib_dir / _name
    if _candidate.is_file():
        _tcl_tk_binaries.append((str(_candidate), "."))

a = Analysis(
    ['src/sig_app.py'],
    pathex=[],
    binaries=_tcl_tk_binaries,
    datas=[
        ('assets/appwin.jpg', 'assets'),
        ('assets/appwin.png', 'assets'),
        ('assets/icon.png', 'assets'),
        ('assets/default_nomes.txt', 'assets'),
    ],
    hiddenimports=[
        '_cffi_backend',
        'sounddevice',
        'websocket',
        'PIL._tkinter_finder',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'silero_vad',
        'silero_vad.utils_vad',
        'silero_vad.model',
        'numpy',
        'onnxruntime',
        'torch',
        'torchaudio',
        'webrtcvad',
        'soundfile',
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='sig',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['assets/icon.png'],
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='sig',
)
