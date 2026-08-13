#!/usr/bin/env bash
# Atualizador do SIG (Linux) — launcher fino.
# A logica transacional completa fica em sig_updater.py (validacao de ZIP,
# journal, lock exclusivo, rollback e validacao de inicializacao).
# Uso: sig_updater.sh --zip <zip> --target <dir> --pid <pid> --log <log>
set -u
DIR="$(cd "$(dirname "$0")" && pwd)"
exec python3 "$DIR/sig_updater.py" "$@"
