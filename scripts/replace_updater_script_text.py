"""Substitui o _update_script_text (bash transacional) pelo launcher fino."""
from pathlib import Path

SRC = Path(r"D:\Projetos\SIG Linux\src\sig_app.py")
text = SRC.read_text(encoding="utf-8")

start = text.index("    @staticmethod\n    def _update_script_text() -> str:")
end = text.index("    def _launch_prepared_update")
launcher = '''    @staticmethod
    def _update_script_text() -> str:
        return r\'\'\'#!/usr/bin/env bash
# Atualizador do SIG (Linux) — launcher fino.
# A logica transacional completa fica em sig_updater.py (validacao de ZIP,
# journal, lock exclusivo, rollback e validacao de inicializacao).
# Uso: sig_updater.sh --zip <zip> --target <dir> --pid <pid> --log <log>
set -u
DIR="$(cd "$(dirname "$0")" && pwd)"
exec python3 "$DIR/sig_updater.py" "$@"
\'\'\'
'''
text = text[:start] + launcher + text[end:]
SRC.write_text(text, encoding="utf-8")
print("OK - _update_script_text agora gera o launcher fino")
