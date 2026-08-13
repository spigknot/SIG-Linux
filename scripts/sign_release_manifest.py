#!/usr/bin/env python3
"""Assina o manifesto da release gerada SEM rebuild (o ZIP já foi enviado).

O release.py sempre faz clean build (não bit-reprodutível). Depois do upload
do ZIP ao Drive, este script injeta o zip_file_id no rascunho
(release/generated/<version>/latest.draft.json), assina com a chave privada
local e valida a assinatura contra a chave pública embutida no aplicativo.

Uso:
    python scripts/sign_release_manifest.py <version> <zip_file_id>

Requisitos:
    - release/update_private_key.pem (a MESMA chave da release anterior;
      nunca gerar chave nova, a pública embutida no app não mudou).
    - release/generated/<version>/latest.draft.json (gerado pelo release.py).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT))

from release import (  # noqa: E402
    read_manifest,
    sign_manifest,
    validate_manifest_shape,
    validate_manifest_signature,
)


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    version = sys.argv[1]
    zip_file_id = sys.argv[2]

    generated = ROOT / "release" / "generated" / version
    draft_path = generated / "latest.draft.json"
    if not draft_path.is_file():
        print(f"FAIL: rascunho não encontrado: {draft_path}")
        return 1

    draft = json.loads(draft_path.read_text(encoding="utf-8"))
    if str(draft.get("version")) != version:
        print(f"FAIL: versão do rascunho ({draft.get('version')}) diverge de {version}")
        return 1
    zip_path = generated / f"{version}.zip"
    if not zip_path.is_file():
        print(f"FAIL: ZIP da release não encontrado: {zip_path}")
        return 1

    draft["zip_file_id"] = zip_file_id
    manifest_path = generated / "latest.json"
    sign_manifest(draft, ROOT / "release" / "update_private_key.pem", manifest_path)
    final_manifest = read_manifest(manifest_path)
    validate_manifest_shape(final_manifest)
    validate_manifest_signature(final_manifest, ROOT / "src" / "sig_app.py")
    print(f"OK: manifesto assinado e validado: {manifest_path}")
    print(f"  version={final_manifest['version']} zip={final_manifest['zip_name']}")
    print(f"  sha256={final_manifest['sha256']}")
    print(f"  size={final_manifest['size']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
