"""Adapta release_validation.py do SIG Linux - parte 3 final."""
from pathlib import Path

SRC = Path(r"D:\Projetos\SIG Linux\scripts\release_validation.py")
text = SRC.read_text(encoding="utf-8")
changes = []

# 1) msg sig.exe -> sig
old = 'f"sig.exe={frozen_version}, APP_VERSION={app_version}"'
new = 'f"sig={frozen_version}, APP_VERSION={app_version}"'
assert old in text
text = text.replace(old, new)
changes.append("msg")

# 2) write_build_info updater
old = '    updater = package_root / "SigUpdater.exe"'
new = '    updater = package_root / "sig_updater.sh"'
assert old in text
text = text.replace(old, new)
changes.append("write_build_info updater")

# 3) validate_build_info sig.exe
old = 'if data.get("sig_sha256") != sha256_file(package_root / "sig.exe"):'
new = 'if data.get("sig_sha256") != sha256_file(package_root / "sig"):'
assert old in text
text = text.replace(old, new)
changes.append("build_info sig")

old = 'raise ValidationError("sig.exe foi alterado depois da geração do build-info.json")'
new = 'raise ValidationError("sig foi alterado depois da geração do build-info.json")'
assert old in text
text = text.replace(old, new)
changes.append("msg build_info")

# 4) validate_updater_artifact
old = '''def validate_updater_artifact(package_root: Path, metadata_path: Path) -> None:
    updater = package_root / "SigUpdater.exe"
    if not updater.is_file():
        raise ValidationError("SigUpdater.exe ausente")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    expected_size = int(metadata.get("size") or 0)
    expected_hash = str(metadata.get("sha256") or "").lower()
    if updater.stat().st_size != expected_size or sha256_file(updater) != expected_hash:
        raise ValidationError(
            "SigUpdater.exe não corresponde ao artefato conhecido como bom; "
            "o código-fonte do updater não está versionado neste projeto"
        )'''
new = '''def validate_updater_artifact(package_root: Path, metadata_path: Path) -> None:
    updater = package_root / "sig_updater.sh"
    if not updater.is_file():
        raise ValidationError("sig_updater.sh ausente")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    expected_size = int(metadata.get("size") or 0)
    expected_hash = str(metadata.get("sha256") or "").lower()
    if updater.stat().st_size != expected_size or sha256_file(updater) != expected_hash:
        raise ValidationError(
            "sig_updater.sh não corresponde ao artefato conhecido como bom; "
            "o código-fonte do updater não está versionado neste projeto"
        )'''
assert old in text
text = text.replace(old, new)
changes.append("updater artifact")

# 5) frozen_app_version call
old = 'frozen_version = frozen_app_version(package_root / "sig.exe")'
new = 'frozen_version = frozen_app_version(package_root / "sig")'
assert old in text
text = text.replace(old, new)
changes.append("frozen call")

# 6) mensagens finais
old = '"SigUpdater.exe corresponde ao artefato conhecido como bom",'
new = '"sig_updater.sh corresponde ao artefato conhecido como bom",'
assert old in text
text = text.replace(old, new)
changes.append("final msg")

SRC.write_text(text, encoding="utf-8")
print("Aplicadas:", *changes, sep="\n  - ")
