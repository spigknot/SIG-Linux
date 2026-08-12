"""Aplica patches do updater (bash) no sig_app.py do SIG Linux."""
from pathlib import Path

SRC = Path(r"D:\Projetos\SIG Linux\src\sig_app.py")
text = SRC.read_text(encoding="utf-8")

# ---- 1) _update_script_text: PowerShell -> bash ----
start = text.index("    @staticmethod\n    def _update_script_text() -> str:")
end = text.index("    def _launch_prepared_update")
bash_script = '''    @staticmethod
    def _update_script_text() -> str:
        return r\'\'\'#!/usr/bin/env bash
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
    if [[ -e "$dst" ]]; then
        mkdir -p "$BACKUP/$(dirname "$dst")"
        mv "$dst" "$BACKUP/$dst" 2>/dev/null || true
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
    ( cd "$work" && nohup "$exe" >/dev/null 2>&1 & )
    log "SIG iniciado."
}

start_sig_and_verify() {
    local exe="$1"
    local work="$(dirname "$exe")"
    ( cd "$work" && nohup "$exe" >/dev/null 2>&1 & )
    local new_pid=$!
    log "Iniciando SIG atualizado diretamente (PID $new_pid)."
    sleep 5
    if ! kill -0 "$new_pid" 2>/dev/null; then
        die "O SIG atualizado encerrou durante a inicializacao."
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
    install_file "$f" "$TARGET/$name"
    copied+=("$name")
done
chmod +x "$TARGET/sig" "$TARGET/sig_updater.sh" 2>/dev/null || true

log "Validando o SIG atualizado."
start_sig_and_verify "$TARGET/sig" || rollback_and_exit
log "Atualizacao aplicada e validada."
rm -rf "$(dirname "$ZIP")" "$BACKUP"
exit 0
\'\'\'
'''
text = text[:start] + bash_script + text[end:]

# ---- 2) _launch_prepared_update: SigUpdater.exe -> sig_updater.sh ----
old = '''        staged_updater = zip_path.parent / "staging" / "SigUpdater.exe"
        updater_path = staged_updater if staged_updater.is_file() else app_base_dir() / "SigUpdater.exe"
        if not updater_path.is_file():
            detail = (
                "SigUpdater.exe não foi encontrado ao lado do SIG. "
                "É necessária uma instalação completa para habilitar "
                "as atualizações automáticas."
            )
            self.update_installing = False
            self.update_button.configure(state="normal")
            self.update_button_var.set("Atualização disponível")
            self._append_activity_log(f"Falha ao iniciar o atualizador: {detail}", "warning")
            messagebox.showerror("Atualização do SIG", detail)
            return
        temporary_updater = (
            Path(tempfile.gettempdir()) /
            f"SigUpdater-{uuid.uuid4().hex}.exe"
        )
        flags = 0
        if os.name == "nt":
            flags = (
                getattr(subprocess, "CREATE_NO_WINDOW", 0)
                | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            )
        try:
            shutil.copy2(updater_path, temporary_updater)
            with log_path.open("a", encoding="utf-8") as log_file:
                source_label = "pacote baixado" if updater_path == staged_updater else "instalação atual"
                log_file.write(
                    f"{time.strftime('%Y-%m-%dT%H:%M:%S')} "
                    f"Usando SigUpdater.exe da {source_label}.\\n"
                )
            subprocess.Popen(
                [
                    str(temporary_updater),
                    "--zip",
                    str(zip_path),
                    "--target",
                    str(app_base_dir()),
                    "--pid",
                    str(os.getpid()),
                    "--log",
                    str(log_path),
                ],
                creationflags=flags,
                close_fds=True,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )'''
new = '''        if os.name == "nt":
            self._launch_prepared_update_windows(zip_path, version, log_path)
            return
        updater_path = app_base_dir() / "sig_updater.sh"
        if not updater_path.is_file():
            detail = (
                "sig_updater.sh não foi encontrado ao lado do SIG. "
                "É necessária uma instalação completa para habilitar "
                "as atualizações automáticas."
            )
            self.update_installing = False
            self.update_button.configure(state="normal")
            self.update_button_var.set("Atualização disponível")
            self._append_activity_log(f"Falha ao iniciar o atualizador: {detail}", "warning")
            messagebox.showerror("Atualização do SIG", detail)
            return
        try:
            with log_path.open("a", encoding="utf-8") as log_file:
                log_file.write(
                    f"{time.strftime('%Y-%m-%dT%H:%M:%S')} "
                    f"Usando sig_updater.sh da instalação atual.\\n"
                )
            subprocess.Popen(
                [
                    "/bin/bash",
                    str(updater_path),
                    "--zip",
                    str(zip_path),
                    "--target",
                    str(app_base_dir()),
                    "--pid",
                    str(os.getpid()),
                    "--log",
                    str(log_path),
                ],
                close_fds=True,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )'''
assert old in text, "_launch_prepared_update"
text = text.replace(old, new)

# ---- 3) helper _launch_prepared_update_windows (mantém o fluxo antigo) ----
old = '''        self._append_activity_log(f"Atualização {version} pronta. Reiniciando o SIG...")
        self.root.after(250, self.root.destroy)'''
new = '''        self._append_activity_log(f"Atualização {version} pronta. Reiniciando o SIG...")
        self.root.after(250, self.root.destroy)

    def _launch_prepared_update_windows(self, zip_path: Path, version: str, log_path: Path) -> None:
        staged_updater = zip_path.parent / "staging" / "SigUpdater.exe"
        updater_path = staged_updater if staged_updater.is_file() else app_base_dir() / "SigUpdater.exe"
        if not updater_path.is_file():
            detail = (
                "SigUpdater.exe não foi encontrado ao lado do SIG. "
                "É necessária uma instalação completa para habilitar "
                "as atualizações automáticas."
            )
            self.update_installing = False
            self.update_button.configure(state="normal")
            self.update_button_var.set("Atualização disponível")
            self._append_activity_log(f"Falha ao iniciar o atualizador: {detail}", "warning")
            messagebox.showerror("Atualização do SIG", detail)
            return
        temporary_updater = (
            Path(tempfile.gettempdir()) /
            f"SigUpdater-{uuid.uuid4().hex}.exe"
        )
        flags = (
            getattr(subprocess, "CREATE_NO_WINDOW", 0)
            | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        )
        try:
            shutil.copy2(updater_path, temporary_updater)
            with log_path.open("a", encoding="utf-8") as log_file:
                source_label = "pacote baixado" if updater_path == staged_updater else "instalação atual"
                log_file.write(
                    f"{time.strftime('%Y-%m-%dT%H:%M:%S')} "
                    f"Usando SigUpdater.exe da {source_label}.\\n"
                )
            subprocess.Popen(
                [
                    str(temporary_updater),
                    "--zip",
                    str(zip_path),
                    "--target",
                    str(app_base_dir()),
                    "--pid",
                    str(os.getpid()),
                    "--log",
                    str(log_path),
                ],
                creationflags=flags,
                close_fds=True,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception as exc:
            with log_path.open("a", encoding="utf-8") as log_file:
                log_file.write(f"{time.strftime('%Y-%m-%dT%H:%M:%S')} Falha ao iniciar o processo auxiliar: {exc}\\n")
            self.update_installing = False
            self.update_button.configure(state="normal")
            self.update_button_var.set("Atualização disponível")
            self._append_activity_log(f"Falha ao iniciar o atualizador: {exc}", "warning")
            messagebox.showerror("Atualização do SIG", f"Não foi possível iniciar o atualizador:\\n{exc}")
            return
        self._append_activity_log(f"Atualização {version} pronta. Reiniciando o SIG...")
        self.root.after(250, self.root.destroy)'''
assert old in text, "root.after(250"
text = text.replace(old, new)

SRC.write_text(text, encoding="utf-8")
print("OK - updater adaptado para Linux (bash) + helper Windows preservado")
