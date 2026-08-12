#!/usr/bin/env python3
"""Publicação do SIG Linux no Google Drive via API (nunca por unidade montada).

Uso:
    python scripts/drive_upload.py auth
    python scripts/drive_upload.py upload <zip>            # -> imprime o ID do ZIP
    python scripts/drive_upload.py publish <manifest.json> # cria/atualiza latest.json -> ID
    python scripts/drive_upload.py verify <file_id> <sha256> [--name <esperado>]

Credenciais: release/credentials.json (client OAuth Desktop) e
release/token_drive.json (token de autorização do Drive, gerado pelo comando auth).
Ambos ficam fora do git (.gitignore). A chave privada do manifesto nunca sai da máquina.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DRIVE_FOLDER_ID = "14NX28WcCAcRuCT7TM8HmSD2IF6yYUOc0"
SCOPES = ["https://www.googleapis.com/auth/drive"]
CREDENTIALS_PATH = ROOT / "release" / "credentials.json"
TOKEN_PATH = ROOT / "release" / "token_drive.json"


def _get_service():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    creds = None
    if TOKEN_PATH.is_file():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDENTIALS_PATH.is_file():
                raise SystemExit(f"credentials.json ausente: {CREDENTIALS_PATH}")
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_PATH), SCOPES)
            creds = flow.run_local_server(port=0, prompt="consent")
        TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")
        print(f"Token salvo em {TOKEN_PATH}")
    return build("drive", "v3", credentials=creds)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def cmd_auth() -> int:
    service = _get_service()
    about = service.about().get(fields="user(emailAddress)").execute()
    print(f"Autenticado como: {about['user']['emailAddress']}")
    return 0


def cmd_upload(args: argparse.Namespace) -> int:
    from googleapiclient.http import MediaFileUpload

    zip_path = Path(args.zip).resolve()
    if not zip_path.is_file():
        raise SystemExit(f"ZIP não encontrado: {zip_path}")
    service = _get_service()
    media = MediaFileUpload(str(zip_path), mimetype="application/zip", resumable=True)
    created = service.files().create(
        body={"name": zip_path.name, "parents": [DRIVE_FOLDER_ID]},
        media_body=media,
        fields="id,name,size,md5Checksum",
    ).execute()
    file_id = created["id"]
    check = service.files().get(fileId=file_id, fields="id,name,size,md5Checksum").execute()
    local_size = zip_path.stat().st_size
    if int(check["size"]) != local_size:
        raise SystemExit(f"tamanho divergente após upload: API={check['size']} local={local_size}")
    print(f"UPLOAD OK: id={file_id} name={check['name']} size={check['size']} md5={check['md5Checksum']}")
    print(file_id)
    return 0


def cmd_publish(args: argparse.Namespace) -> int:
    from googleapiclient.http import MediaFileUpload

    manifest_path = Path(args.manifest).resolve()
    if not manifest_path.is_file():
        raise SystemExit(f"manifesto não encontrado: {manifest_path}")
    service = _get_service()
    query = f"name='latest.json' and '{DRIVE_FOLDER_ID}' in parents and trashed=false"
    existing = service.files().list(q=query, fields="files(id,name)").execute().get("files", [])
    media = MediaFileUpload(str(manifest_path), mimetype="application/json")
    if existing:
        file_id = existing[0]["id"]
        service.files().update(fileId=file_id, media_body=media, fields="id").execute()
        action = "atualizado"
    else:
        created = service.files().create(
            body={"name": "latest.json", "parents": [DRIVE_FOLDER_ID]},
            media_body=media,
            fields="id",
        ).execute()
        file_id = created["id"]
        action = "criado"
    check = service.files().get(fileId=file_id, fields="id,name,size").execute()
    if int(check["size"]) != manifest_path.stat().st_size:
        raise SystemExit("tamanho divergente após publicação do manifesto")
    print(f"MANIFESTO {action}: id={file_id} name={check['name']} size={check['size']}")
    print(file_id)
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    service = _get_service()
    meta = service.files().get(fileId=args.file_id, fields="id,name,size,md5Checksum").execute()
    print(f"API: id={meta['id']} name={meta['name']} size={meta['size']} md5={meta['md5Checksum']}")
    if args.name and meta["name"] != args.name:
        raise SystemExit(f"nome divergente: API={meta['name']} esperado={args.name}")
    tmp = Path(tempfile.gettempdir()) / f"sig_drive_verify_{meta['name']}"
    request = service.files().get_media(fileId=args.file_id)
    from googleapiclient.http import MediaIoBaseDownload

    with tmp.open("wb") as handle:
        downloader = MediaIoBaseDownload(handle, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
    actual = _sha256(tmp)
    tmp.unlink(missing_ok=True)
    expected = args.sha256.lower()
    if actual != expected:
        raise SystemExit(f"SHA-256 divergente: baixado={actual} esperado={expected}")
    print(f"VERIFY OK: sha256={actual}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Publicação do SIG Linux no Google Drive")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("auth", help="gerar/renovar o token de autorização do Drive")
    upload = sub.add_parser("upload", help="fazer upload do ZIP incremental")
    upload.add_argument("zip", help="caminho do ZIP (YYYYMMDD_NNN.zip)")
    publish = sub.add_parser("publish", help="criar/atualizar o latest.json assinado")
    publish.add_argument("manifest", help="caminho do latest.json assinado")
    verify = sub.add_parser("verify", help="conferir arquivo publicado pela API (tamanho + sha256)")
    verify.add_argument("file_id", help="ID do arquivo no Drive")
    verify.add_argument("sha256", help="sha256 esperado")
    verify.add_argument("--name", help="nome esperado do arquivo")
    args = parser.parse_args()
    try:
        if args.command == "auth":
            return cmd_auth()
        if args.command == "upload":
            return cmd_upload(args)
        if args.command == "publish":
            return cmd_publish(args)
        if args.command == "verify":
            return cmd_verify(args)
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
