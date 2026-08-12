"""Adapta release_validation.py do Windows para o SIG Linux."""
from pathlib import Path

SRC = Path(r"D:\Projetos\SIG Linux\scripts\release_validation.py")
text = SRC.read_text(encoding="utf-8")
changes = []

# 1) Docstring + arquivos obrigatórios
old = '''REQUIRED_FULL_FILES = (
    "sig.exe",
    "_internal/base_library.zip",
    "_internal/python311.dll",
    "_internal/vcruntime140.dll",
    "_internal/vcruntime140_1.dll",
    "_internal/_sounddevice_data/portaudio-binaries/libportaudio64bit.dll",
    "SigUpdater.exe",
    "ffmpeg.exe",
    "ffplay.exe",
    "vad_worker.py",
)
REQUIRED_FULL_DIRECTORIES = ("_internal", "vad_deps")
RUNTIME_ASSET_FILES = ("ffmpeg.exe", "ffplay.exe")
RUNTIME_ASSET_DIRECTORIES = ("vad_deps",)'''
new = '''REQUIRED_FULL_FILES = (
    "sig",
    "_internal/base_library.zip",
    "sig_updater.sh",
    "ffmpeg",
    "ffplay",
    "vad_worker.py",
)
REQUIRED_FULL_DIRECTORIES = ("_internal", "vad_deps")
RUNTIME_ASSET_FILES = ("ffmpeg", "ffplay")
RUNTIME_ASSET_DIRECTORIES = ("vad_deps",)'''
assert old in text, "REQUIRED_FULL_FILES"
text = text.replace(old, new)
changes.append("REQUIRED_FULL_FILES/RUNTIME_ASSET_FILES")

# 2) source_fingerprint: updater_v2/updater.py -> updater_linux/sig_updater.sh
old = '''        "src/sig_app.py",
        "src/vad_worker.py",
        "src/assistant_prompts.py",
        "updater_v2/updater.py",
        "sig.spec",
        "requirements.txt",'''
new = '''        "src/sig_app.py",
        "src/vad_worker.py",
        "src/assistant_prompts.py",
        "updater_linux/sig_updater.sh",
        "sig.spec",
        "requirements.txt",'''
assert old in text, "source_fingerprint"
text = text.replace(old, new)
changes.append("source_fingerprint")

SRC.write_text(text, encoding="utf-8")
print("Aplicadas:", *changes, sep="\n  - ")
