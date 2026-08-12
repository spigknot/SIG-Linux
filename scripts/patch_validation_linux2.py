"""Adapta release_validation.py do SIG Linux - parte 2 (executável, PortAudio)."""
from pathlib import Path

SRC = Path(r"D:\Projetos\SIG Linux\scripts\release_validation.py")
text = SRC.read_text(encoding="utf-8")
changes = []

# 1) validate_frozen_dependencies: sig.exe -> sig; PortAudio DLL -> so
old = '''def validate_frozen_dependencies(package_root: Path) -> None:
    executable = package_root / "sig.exe"'''
new = '''def validate_frozen_dependencies(package_root: Path) -> None:
    executable = package_root / "sig"'''
assert old in text, "validate_frozen_dependencies exe"
text = text.replace(old, new)
changes.append("validate_frozen_dependencies: sig")

old = '''    portaudio = package_root / "_internal/_sounddevice_data/portaudio-binaries/libportaudio64bit.dll"
    if not portaudio.is_file():
        raise ValidationError(f"DLL do PortAudio ausente: {portaudio}")'''
new = '''    # No Linux o PortAudio vem do sistema (libportaudio.so.2); a checagem de
    # dependência congelada é satisfeita pelos módulos do PYZ acima.
    candidates = [
        package_root / "_internal/_sounddevice_data/portaudio-binaries/libportaudio64bit.dll",
        Path("/usr/lib/x86_64-linux-gnu/libportaudio.so.2"),
        Path("/usr/lib/aarch64-linux-gnu/libportaudio.so.2"),
        Path("/usr/lib/libportaudio.so.2"),
    ]
    if not any(path.is_file() for path in candidates):
        raise ValidationError(
            "PortAudio não encontrado no pacote nem no sistema; instale libportaudio2"
        )'''
assert old in text, "portaudio check"
text = text.replace(old, new)
changes.append("PortAudio linux")

# 2) write_build_info: sig.exe -> sig
old = '''    executable = package_root / "sig.exe"'''
new = '''    executable = package_root / "sig"'''
assert old in text, "write_build_info exe"
text = text.replace(old, new)
changes.append("write_build_info: sig")

SRC.write_text(text, encoding="utf-8")
print("Aplicadas:", *changes, sep="\n  - ")
