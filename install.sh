#!/usr/bin/env bash
# Instalador do SIG Linux.
# Uso: curl -fsSL https://raw.githubusercontent.com/spigknot/SIG-Linux/main/install.sh | bash
# Baixa o pacote oficial do Google Drive (canal de publicação), confere o
# sha256 contra o manifesto assinado e instala em ~/.local/share/sig.
set -euo pipefail

MANIFEST_ID="14qU9b4wbyu7_6hAOvip6qhSG91E45BJ3"
DL_URL="https://drive.usercontent.google.com/download"
# confirm=t pula a página de confirmação do Drive para arquivos > 100 MB
# (mesmo mecanismo usado pelo app em src/sig_app.py: google_drive_download_url).

INSTALL_DIR="${SIG_INSTALL_DIR:-$HOME/.local/share/sig}"
BIN_DIR="${SIG_BIN_DIR:-$HOME/.local/bin}"
APP_DIR="$HOME/.local/share/applications"
TMP_ZIP="$(mktemp /tmp/sig_install_XXXXXX.zip)"
TMP_MAN="$(mktemp /tmp/sig_manifest_XXXXXX.json)"

cleanup() { rm -f "$TMP_ZIP" "$TMP_MAN"; }
trap cleanup EXIT

echo "==> Verificando requisitos..."
MISSING=""
command -v unzip >/dev/null 2>&1 || MISSING="$MISSING unzip"
command -v python3 >/dev/null 2>&1 || MISSING="$MISSING python3"
command -v curl >/dev/null 2>&1 || MISSING="$MISSING curl"
[ -n "$MISSING" ] && { echo "ERRO: faltam pacotes:$MISSING"; exit 1; }
if ! command -v ffmpeg >/dev/null 2>&1; then
    echo "AVISO: ffmpeg não encontrado no sistema (sudo apt install ffmpeg). O pacote inclui um binário, mas o do sistema é recomendado."
fi

echo "==> Baixando manifesto ($MANIFEST_ID)..."
curl -fsSL "$DL_URL?id=$MANIFEST_ID&export=download&confirm=t" -o "$TMP_MAN"
VERSION="$(python3 -c "import json;print(json.load(open('$TMP_MAN'))['version'])")"
ZIP_ID="$(python3 -c "import json;print(json.load(open('$TMP_MAN'))['zip_file_id'])")"
ZIP_NAME="$(python3 -c "import json;print(json.load(open('$TMP_MAN'))['zip_name'])")"
SHA256_EXPECTED="$(python3 -c "import json;print(json.load(open('$TMP_MAN'))['sha256'])")"
SIZE_EXPECTED="$(python3 -c "import json;print(json.load(open('$TMP_MAN'))['size'])")"

INSTALLED_VERSION=""
if [ -f "$INSTALL_DIR/build-info.json" ]; then
    INSTALLED_VERSION="$(python3 -c "import json;print(json.load(open('$INSTALL_DIR/build-info.json'))['version'])" 2>/dev/null || true)"
fi
if [ -n "$INSTALLED_VERSION" ] && [ "$INSTALLED_VERSION" = "$VERSION" ] && [ "${SIG_FORCE:-0}" != "1" ]; then
    echo "SIG já está na versão $VERSION ($INSTALL_DIR). Nada a fazer."
    echo "Para reinstalar/forçar: SIG_FORCE=1 bash install.sh"
    exit 0
fi
if [ -n "$INSTALLED_VERSION" ]; then
    echo "==> Atualizando SIG $INSTALLED_VERSION -> $VERSION ..."
else
    echo "==> Instalando SIG $VERSION ..."
fi

echo "==> Baixando SIG $VERSION ($((SIZE_EXPECTED / 1024 / 1024)) MB) do Drive..."
curl -fsSL "$DL_URL?id=$ZIP_ID&export=download&confirm=t" -o "$TMP_ZIP"

echo "==> Conferindo integridade..."
ACTUAL_SIZE="$(stat -c%s "$TMP_ZIP")"
[ "$ACTUAL_SIZE" -eq "$SIZE_EXPECTED" ] || { echo "ERRO: tamanho divergente ($ACTUAL_SIZE != $SIZE_EXPECTED)"; exit 1; }
if command -v sha256sum >/dev/null 2>&1; then
    ACTUAL_SHA="$(sha256sum "$TMP_ZIP" | cut -d' ' -f1)"
    [ "$ACTUAL_SHA" = "$SHA256_EXPECTED" ] || { echo "ERRO: sha256 divergente ($ACTUAL_SHA != $SHA256_EXPECTED)"; exit 1; }
    echo "sha256 OK: $ACTUAL_SHA"
else
    echo "AVISO: sha256sum não encontrado; pulando conferência de hash."
fi

echo "==> Instalando em $INSTALL_DIR ..."
mkdir -p "$INSTALL_DIR"
unzip -qo "$TMP_ZIP" -d "$INSTALL_DIR"
chmod +x "$INSTALL_DIR/sig" "$INSTALL_DIR/sig_updater.sh" 2>/dev/null || true

echo "==> Criando comando 'sig' em $BIN_DIR ..."
mkdir -p "$BIN_DIR"
cat > "$BIN_DIR/sig" <<EOF
#!/usr/bin/env bash
exec "$INSTALL_DIR/sig" "\$@"
EOF
chmod +x "$BIN_DIR/sig"

echo "==> Criando lançador do menu ..."
mkdir -p "$APP_DIR"
cat > "$APP_DIR/sig.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=SIG
Comment=Transcrição e processamento de áudio
Exec=$BIN_DIR/sig
Icon=$INSTALL_DIR/_internal/assets/icon.png
Terminal=false
Categories=Utility;AudioVideo;
EOF
chmod +x "$APP_DIR/sig.desktop" 2>/dev/null || true

echo "==> Criando atalho na Área de Trabalho ..."
DESKTOP_DIR="${SIG_DESKTOP_DIR:-}"
if [ -z "$DESKTOP_DIR" ]; then
    DESKTOP_DIR="$(xdg-user-dir DESKTOP 2>/dev/null || true)"
    [ -n "$DESKTOP_DIR" ] || DESKTOP_DIR="$HOME/Desktop"
    [ -d "$DESKTOP_DIR" ] || DESKTOP_DIR="$HOME/Área de Trabalho"
fi
mkdir -p "$DESKTOP_DIR" 2>/dev/null || true
if [ -d "$DESKTOP_DIR" ]; then
    cp "$APP_DIR/sig.desktop" "$DESKTOP_DIR/SIG.desktop"
    chmod +x "$DESKTOP_DIR/SIG.desktop" 2>/dev/null || true
    # Marca como confiável para o XFCE/GNOME abrir sem pedir confirmação.
    command -v gio >/dev/null 2>&1 && gio set "$DESKTOP_DIR/SIG.desktop" metadata::trusted true 2>/dev/null || true
    echo "   Atalho: $DESKTOP_DIR/SIG.desktop"
else
    echo "   AVISO: pasta de Área de Trabalho não encontrada; atalho não criado."
fi

echo ""
echo "✅ SIG $VERSION instalado!"
echo "   App:    $INSTALL_DIR"
echo "   Comando: sig"
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    echo "   ⚠️  $BIN_DIR não está no PATH. Adicione com:"
    echo "      echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.bashrc && source ~/.bashrc"
fi
echo "   Para abrir agora: $BIN_DIR/sig  (ou pelo menu de aplicativos)"
