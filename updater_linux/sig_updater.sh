#!/usr/bin/env bash
# Atualizador do SIG (Linux) - equivalente ao SigUpdater.exe do Windows.
# Uso: sig_updater.sh --zip <zip> --target <dir> --pid <pid> --log <log>
set -u

ZIP=""
TARGET=""
PID=""
LOG=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --zip) ZIP="$2"; shift 2 ;;
        --target) TARGET="$2"; shift 2 ;;
        --pid) PID="$2"; shift 2 ;;
        --log) LOG="$2"; shift 2 ;;
        *) shift ;;
    esac
done

log() { echo "$(date +%Y-%m-%dT%H:%M:%S) $*" >> "$LOG"; }
die() { log "FALHA: $*"; exit 1; }

mkdir -p "$(dirname "$LOG")"
log "Atualizador iniciado."

original_target="$TARGET"
current="$TARGET"
for _ in 1 2 3 4 5 6; do
    if [[ -f "$current/ffmpeg" || -f "$current/ffplay" || -d "$current/vad_deps" || -f "$current/ffmpeg.exe" ]]; then
        TARGET="$current"
        break
    fi
    parent="$(dirname "$current")"
    [[ "$parent" == "$current" ]] && break
    current="$parent"
done
log "Destino recebido=$original_target; destino resolvido=$TARGET; origem=$(dirname "$ZIP")"

deadline=$(( $(date +%s) + 120 ))
while kill -0 "$PID" 2>/dev/null; do
    if [[ $(date +%s) -ge $deadline ]]; then
        log "Tempo esgotado aguardando o SIG fechar."
        exit 2
    fi
    sleep 0.25
done
log "SIG encerrado; aplicando arquivos."
sleep 2

BACKUP="$(mktemp -d "/tmp/sig_backup_XXXXXX")"
STAGING="$(dirname "$ZIP")/staging"
declare -a replaced_dirs=()
declare -a copied=()

install_file() {
    local src="$1" dst="$2"
    local rel="${dst#"$TARGET"/}"
    if [[ -e "$dst" ]]; then
        mkdir -p "$BACKUP/$(dirname "$rel")"
        mv "$dst" "$BACKUP/$rel" 2>/dev/null || true
    fi
    mkdir -p "$(dirname "$dst")"
    cp -f "$src" "$dst" || die "nao foi possivel copiar $src -> $dst"
}

restore_backup() {
    for rel in "${copied[@]}"; do
        if [[ -e "$BACKUP/$rel" ]]; then
            cp -f "$BACKUP/$rel" "$TARGET/$rel" 2>/dev/null || true
        fi
    done
    for rel in "${replaced_dirs[@]}"; do
        if [[ -d "$BACKUP/$rel" ]]; then
            rm -rf "$TARGET/$rel"
            cp -a "$BACKUP/$rel" "$TARGET/$rel" 2>/dev/null || true
        fi
    done
}

start_sig() {
    local exe="$1"
    local work="$(dirname "$exe")"
    cd "$work" || return 1
    nohup "$exe" >/dev/null 2>&1 &
    disown 2>/dev/null || true
    log "SIG iniciado."
}

start_sig_and_verify() {
    local exe="$1"
    local work="$(dirname "$exe")"
    cd "$work" || return 1
    nohup "$exe" >/dev/null 2>&1 &
    local new_pid=$!
    disown 2>/dev/null || true
    log "Iniciando SIG atualizado diretamente (PID $new_pid)."
    sleep 5
    if ! kill -0 "$new_pid" 2>/dev/null; then
        log "O SIG atualizado encerrou durante a inicializacao."
        return 1
    fi
    return 0
}

rollback_and_exit() {
    log "Aplicando rollback."
    restore_backup
    if [[ -x "$TARGET/sig" ]]; then
        start_sig "$TARGET/sig"
    fi
    exit 1
}

log "Validando zip: $ZIP"
python3 - "$ZIP" <<'PYEOF' || die "zip invalido"
import sys, zipfile
z = zipfile.ZipFile(sys.argv[1])
bad = z.testzip()
if bad is not None:
    sys.exit(1)
names = [i.filename for i in z.infolist()]
required = {"sig", "_internal/base_library.zip", "sig_updater.sh"}
missing = [r for r in required if not any(n.replace(chr(92), "/").lower() == r.lower() for n in names)]
if missing:
    print("missing:", missing, file=sys.stderr)
    sys.exit(1)
PYEOF

log "Extraindo staging."
rm -rf "$STAGING"
mkdir -p "$STAGING"
(cd "$STAGING" && unzip -q "$ZIP" 2>/dev/null || python3 -m zipfile -e "$ZIP" .) || die "falha ao extrair zip"

log "Aplicando atualizacao (staging -> target)."
for dirname in _internal; do
    if [[ -d "$STAGING/$dirname" ]]; then
        if [[ -d "$TARGET/$dirname" ]]; then
            mkdir -p "$BACKUP/$dirname"
            mv "$TARGET/$dirname" "$BACKUP/$dirname"
            replaced_dirs+=("$dirname")
        fi
        cp -a "$STAGING/$dirname" "$TARGET/$dirname" || die "falha ao instalar $dirname"
    fi
done
for f in "$STAGING"/*; do
    name="$(basename "$f")"
    [[ "$name" == "_internal" ]] && continue
    if [[ -d "$f" ]]; then
        if [[ -d "$TARGET/$name" ]]; then
            mkdir -p "$BACKUP/$name"
            mv "$TARGET/$name" "$BACKUP/$name"
            replaced_dirs+=("$name")
        fi
        cp -a "$f" "$TARGET/$name" || die "falha ao instalar $name"
    else
        install_file "$f" "$TARGET/$name"
        copied+=("$name")
    fi
done
chmod +x "$TARGET/sig" "$TARGET/sig_updater.sh" 2>/dev/null || true

log "Validando o SIG atualizado."
start_sig_and_verify "$TARGET/sig" || rollback_and_exit
log "Atualizacao aplicada e validada."
rm -rf "$(dirname "$ZIP")" "$BACKUP"
exit 0
