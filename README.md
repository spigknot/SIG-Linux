# SIG Linux

Versão Linux do **SIG** — aplicativo desktop de transcrição/processamento de áudio para uso policial (transcrição ao vivo, transcrição de arquivos, qualificação, IMEI, FFmpeg, histórico e oitiva).

Migrado do SIG Windows (Python/Tkinter/PyInstaller). Build **one-dir** com PyInstaller, atualização incremental assinada publicada via API do Google Drive.

## Arquitetura

```
Usuário → sig (executável PyInstaller one-dir, Tkinter GUI)
            ├─ subprocess → ffmpeg/ffplay (conversão, preview)
            ├─ subprocess → python3 vad_worker.py (VAD Silero/WebRTC, lê vad_deps/)
            ├─ HTTP POST → Servidores Granite (transcrição remota)
            └─ Google Drive API → atualizações incrementais (manifesto assinado)
```

## Componentes do pacote (mesma pasta da instalação)

| Componente | Descrição |
|---|---|
| `sig` | Executável one-dir do PyInstaller |
| `_internal/` | Runtime do PyInstaller (libpython3.11.so.1.0, tkinter, sounddevice etc.) |
| `ffmpeg` / `ffplay` | Binários Linux (sem extensão) |
| `vad_deps/` | numpy, onnxruntime, torch, silero-vad, webrtcvad (externos ao exe) |
| `vad_worker.py` | Processador de VAD rodado como subprocesso |
| `sig_updater.sh` | Launcher do atualizador transacional |
| `sig_updater.py` | Lógica do atualizador (validação de ZIP, lock, journal, rollback) |
| `prompts/` | Prompts editáveis (histórico, oitiva, partes, qualificação) |
| `modelos/` | Modelos Word editáveis (declarações e depoimento) |

## Requisitos

- Linux (Debian/Ubuntu recomendado)
- Python 3.11 para build; `python3` no runtime (usado pelo VAD e pelo updater)
- Pacotes de sistema: `ffmpeg`, `libportaudio2`, `unzip`
- GPU não é necessária — o VAD roda em CPU

## Build e release (resumo)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt cryptography
pip install --target dist/vad_deps numpy onnxruntime silero-vad webrtcvad-wheels torch

# Build one-dir
python -m PyInstaller --noconfirm --clean --distpath dist --workpath build sig.spec

# Copiar assets externos para dist/sig/: ffmpeg, ffplay, vad_deps/, vad_worker.py, sig_updater.sh

# Gates oficiais
python scripts/release.py tests
python scripts/release.py validate --warn-path build/sig/warn-sig.txt
python scripts/release.py updater-test --package-zip <zip-de-teste> --updater updater_linux/sig_updater.sh

# Release completa (após upload do ZIP ao Drive)
python scripts/release.py release --version <APP_VERSION> --zip-file-id <ID_DO_ZIP_NO_DRIVE>
```

Regras completas em [AGENTS.md](AGENTS.md).

## Atualizações

- O app verifica `latest.json` na pasta do Drive e oferece o ZIP incremental.
- O `sig_updater.sh` é gerado por `_update_script_text()` em `src/sig_app.py` e materializado em `updater_linux/sig_updater.sh` por `scripts/materialize_updater.py`.
- O updater é transacional: valida o ZIP, faz backup, aplica, valida a inicialização do SIG novo por 5s e faz rollback em falha.

## Estrutura do projeto

```
src/               Código-fonte (sig_app.py ~13.100 linhas, vad_worker.py, assistant_prompts.py)
scripts/           release.py (gates), release_validation.py, materialize_updater.py, patch_* (histórico da migração)
tests/             Regressões dos gates de release
updater_linux/     sig_updater.sh (versionado), harness.py (teste do updater), test_updater.py
assets/            Imagens e ícones
sig.spec           Spec do PyInstaller (one-dir, COLLECT)
```

## Segurança

- Chaves de API nunca no código-fonte, executável ou releases.
- `release/update_private_key.pem` nunca vai para GitHub/Drive.
- Binários grandes (`ffmpeg`, `ffplay`, `vad_deps/`) não entram no Git — entram no pacote da release.
