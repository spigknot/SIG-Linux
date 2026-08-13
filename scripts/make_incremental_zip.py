#!/usr/bin/env python3
"""Gera o ZIP incremental (delta) de uma release e assina o manifesto.

Política de publicação: o pacote FULL vai para o GitHub Releases; o Google
Drive recebe a INCREMENTAL (sig + _internal + updaters + prompts/modelos,
sem ffmpeg/ffplay/vad_worker.py/vad_deps), que é o que o app baixa nas
atualizações.

Uso:
    python scripts/make_incremental_zip.py <version> <zip_file_id>

- Lê o pacote full em release/generated/<version>/package/.
- Monta release/generated/<version>/<version>-incremental.zip com os
  REQUIRED_UPDATE_FILES do updater (sem recursos de runtime).
- Assina release/generated/<version>/latest.json com a chave privada
  (mesma chave de sempre) e valida contra a pública embutida no app.
"""
from __future__ import annotations

import json
import sys
import time
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT))

from release import read_manifest, sha256_file, sign_manifest  # noqa: E402
from release_validation import validate_manifest_shape, validate_manifest_signature  # noqa: E402

INCREMENTAL_EXCLUDED_TOP_LEVEL = {"ffmpeg", "ffplay", "vad_worker.py", "vad_deps"}
INCREMENTAL_REQUIRED_FILES = {
    "sig",
    "_internal/base_library.zip",
    "_internal/libpython3.11.so.1.0",
    "sig_updater.py",
    "sig_updater.sh",
}


def _zip_directory(source: Path, destination: Path, excluded: set[str]) -> None:
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=1) as archive:
        for path in sorted(source.rglob("*")):
            if not path.is_file():
                continue
            relative = path.relative_to(source)
            top = relative.parts[0] if relative.parts else ""
            if top in excluded:
                continue
            archive.write(path, relative.as_posix())


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    version = sys.argv[1]
    zip_file_id = sys.argv[2]

    generated = ROOT / "release" / "generated" / version
    package = generated / "package"
    if not package.is_dir():
        print(f"FAIL: pacote não encontrado: {package}")
        return 1

    zip_name = f"{version}-incremental.zip"
    zip_path = generated / zip_name
    if zip_path.exists():
        zip_path.unlink()
    _zip_directory(package, zip_path, INCREMENTAL_EXCLUDED_TOP_LEVEL)

    with zipfile.ZipFile(zip_path) as archive:
        names = {entry.filename for entry in archive.infolist()}
    missing = sorted(INCREMENTAL_REQUIRED_FILES - names)
    if missing:
        print(f"FAIL: incremental sem membros obrigatórios: {missing}")
        return 1
    leaked = sorted(n for n in names if n.split("/", 1)[0] in INCREMENTAL_EXCLUDED_TOP_LEVEL)
    if leaked:
        print(f"FAIL: incremental contém recursos de runtime: {leaked}")
        return 1

    manifest = {
        "schema": 1,
        "version": version,
        "zip_file_id": zip_file_id,
        # zip_name é o nome do arquivo NO DRIVE: por compatibilidade com apps
        # já publicados (que exigem zip_name == f"{version}.zip"), o nome
        # canônico é <version>.zip — o arquivo local pode ter outro nome e é
        # renomeado no Drive via `drive_upload.py rename`.
        "zip_name": f"{version}.zip",
        "sha256": sha256_file(zip_path),
        "size": zip_path.stat().st_size,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    manifest_path = generated / "latest.json"
    sign_manifest(manifest, ROOT / "release" / "update_private_key.pem", manifest_path)
    final = read_manifest(manifest_path)
    validate_manifest_shape(final)
    validate_manifest_signature(final, ROOT / "src" / "sig_app.py")

    print(f"OK: incremental e manifesto prontos")
    print(f"  zip: {zip_path} ({manifest['size']} bytes)")
    print(f"  sha256: {manifest['sha256']}")
    print(f"  manifesto assinado: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
