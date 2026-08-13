"""Adapta updater_v2/updater.py (Windows) para o SIG Linux: sig_updater.py."""
from pathlib import Path

SRC = Path(r"D:\Projetos\SIG Linux\updater_linux\sig_updater.py")
text = SRC.read_text(encoding="utf-8")
changes = []


def rep(old, new, label):
    global text
    assert text.count(old) == 1, f"{label}: {text.count(old)} ocorrências"
    text = text.replace(old, new)
    changes.append(label)


# 1) Docstring + nomes de arquivos obrigatórios
rep('''"""Transactional updater for the SIG Windows onedir app.''',
    '''"""Transactional updater for the SIG Linux onedir app.''',
    "docstring")

rep('''REQUIRED_CORE_FILES = (
    "sig.exe",
    "_internal/base_library.zip",
    "_internal/python311.dll",
    "_internal/vcruntime140.dll",
    "_internal/vcruntime140_1.dll",
    "_internal/_sounddevice_data/portaudio-binaries/libportaudio64bit.dll",
)
REQUIRED_RUNTIME_FILES = (
    "ffmpeg.exe",
    "ffplay.exe",
    "vad_worker.py",
)
REQUIRED_UPDATE_FILES = REQUIRED_CORE_FILES + ("SigUpdater.exe",)''',
    '''REQUIRED_CORE_FILES = (
    "sig",
    "_internal/base_library.zip",
    "_internal/libpython3.11.so.1.0",
)
REQUIRED_RUNTIME_FILES = (
    "ffmpeg",
    "ffplay",
    "vad_worker.py",
)
REQUIRED_UPDATE_FILES = REQUIRED_CORE_FILES + ("sig_updater.py", "sig_updater.sh")''',
    "required files")

# 2) ALLOWED_TOP_LEVEL_NAMES
rep('''ALLOWED_TOP_LEVEL_NAMES = {
    "sig.exe",
    "_internal",
    "SigUpdater.exe",
    "ffmpeg.exe",
    "ffplay.exe",
    "vad_worker.py",
    "vad_deps",
    "prompts",
    "modelos",
    "build-info.json",
    # These directories are created by the running application and are not
    # part of an update package.
    "temp",
    "cache",
    "logs",
}''',
    '''ALLOWED_TOP_LEVEL_NAMES = {
    "sig",
    "_internal",
    "sig_updater.py",
    "sig_updater.sh",
    "ffmpeg",
    "ffplay",
    "vad_worker.py",
    "vad_deps",
    "prompts",
    "modelos",
    "build-info.json",
    # These directories are created by the running application and are not
    # part of an update package.
    "temp",
    "cache",
    "logs",
}''',
    "top level names")

# 3) _process_image_paths: implementar via /proc no Linux (paridade com o
#    escaneamento por imagem do Windows)
rep('''def _process_image_paths() -> dict[int, str]:
    if os.name != "nt":
        return {}''',
    '''def _linux_process_image_paths() -> dict[int, str]:
    result: dict[int, str] = {}
    try:
        entries = os.listdir("/proc")
    except OSError:
        return result
    for entry in entries:
        if not entry.isdigit():
            continue
        pid = int(entry)
        if pid == os.getpid():
            continue
        try:
            result[pid] = os.readlink(f"/proc/{entry}/exe")
        except OSError:
            continue
    return result


def _process_image_paths() -> dict[int, str]:
    if os.name != "nt":
        return _linux_process_image_paths()''',
    "process image paths linux")

# 4) _launch_and_verify: nome do exe + sem flags Windows
rep('''        process = subprocess.Popen(
            [str(target_exe)],
            cwd=str(target_exe.parent),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=flags,
        )''',
    '''        process = subprocess.Popen(
            [str(target_exe)],
            cwd=str(target_exe.parent),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=flags,
            start_new_session=True,
        )''',
    "launch and verify")

# 5) _apply_transaction: sig.exe -> sig
rep('started_process = _launch_and_verify(target / "sig.exe", startup_timeout, log_path)',
    'started_process = _launch_and_verify(target / "sig", startup_timeout, log_path)',
    "apply transaction exe")

# 6) execute: sig.exe -> sig em _wait_for_processes
rep('_wait_for_processes(pid, target / "sig.exe", wait_timeout, log_path)',
    '_wait_for_processes(pid, target / "sig", wait_timeout, log_path)',
    "execute exe")

# 7) rollback relança sig
rep('_launch_and_verify(target / "sig.exe", min(startup_timeout, 5), log_path)',
    '_launch_and_verify(target / "sig", min(startup_timeout, 5), log_path)',
    "rollback relaunch")

# 8) validate_target_shell: componentes Linux
rep('''    required = {"sig.exe", "_internal", "SigUpdater.exe", "ffmpeg.exe", "ffplay.exe", "vad_deps"}''',
    '''    required = {"sig", "_internal", "sig_updater.py", "sig_updater.sh", "ffmpeg", "ffplay", "vad_deps"}''',
    "target shell")

SRC.write_text(text, encoding="utf-8")
print("Aplicadas:", *changes, sep="\n  - ")
