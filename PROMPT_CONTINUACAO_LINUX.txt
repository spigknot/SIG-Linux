# PROMPT OFICIAL — CONTINUAÇÃO DO DESENVOLVIMENTO DO SIG LINUX

Você é um agente de IA responsável por finalizar, validar e publicar o **SIG Linux** — a versão Linux do aplicativo SIG (transcrição policial, FFmpeg, VAD e ferramentas auxiliares). O projeto foi migrado do SIG Windows (Python/Tkinter/PyInstaller) e está **parcialmente adaptado**. Seu trabalho é: completar as pendências, executar TODOS os gates de validação, corrigir o que falhar, e deixar o app funcionando e publicável no Linux. Trabalhe com método, em etapas, e NUNCA pule os testes.

## LOCALIZAÇÃO DO PROJETO E DO DRIVE

- **Pasta do projeto (SMB):** `smb://taguai/projetos/SIG Linux`
  - ⚠️ **IMPORTANTE:** o share SMB **já está montado e liberado** para você (agente de IA) — não precisa montar nada, não use `mount`, não peça credenciais. Acesse diretamente a pasta `SIG Linux/` no caminho já disponível na sua máquina. Toda a estrutura descrita neste prompt está nessa pasta.
- **Pasta de referência — SIG Windows (SMB):** `smb://taguai/projetos/SIG Windows`
  - ⚠️ Também **já está montada e liberada** para você. Use-a **somente como referência** para comparar funcionalidades, comportamento e regras do app original (ex.: conferir `src/sig_app.py`, `AGENTS.md`, `sig.spec`, `scripts/`). **NÃO altere, não compile, não publique nada dentro do SIG Windows** — ele é somente leitura para você. Todo trabalho de edição/build/release é feito no SIG Linux.
- **Pasta do Google Drive para updates incrementais:** https://drive.google.com/drive/folders/14NX28WcCAcRuCT7TM8HmSD2IF6yYUOc0
  - O ID da pasta é: `14NX28WcCAcRuCT7TM8HmSD2IF6yYUOc0`
  - É nela que o ZIP incremental (`YYYYMMDD_NNN.zip`) e o manifesto `latest.json` assinado serão publicados via API do Google Drive (nunca por cópia manual de unidade montada).

---

## 1. CONTEXTO E ARQUITETURA

O SIG é um app desktop de transcrição/processamento de áudio. No Linux ele é **Python 3.11 + Tkinter + PyInstaller (one-dir)**. Arquitetura:

```
Usuário → sig (executável PyInstaller one-dir, Tkinter GUI)
            ├─ subprocess → ffmpeg/ffplay (conversão, preview)
            ├─ subprocess → python3 vad_worker.py (VAD Silero/WebRTC, lê vad_deps/)
            ├─ HTTP POST → Servidores Granite (transcrição remota)
            └─ Google Drive API → atualizações incrementais (manifesto assinado)
```

Componentes do pacote final (todos na MESMA pasta da instalação):
- `sig` — executável one-dir do PyInstaller
- `_internal/` — runtime do PyInstaller (libpython, tkinter, sounddevice, etc.)
- `ffmpeg` e `ffplay` — binários Linux (sem extensão)
- `vad_deps/` — numpy, onnxruntime, torch, silero-vad, webrtcvad (externo ao exe)
- `vad_worker.py` — processador de VAD rodado como subprocesso
- `sig_updater.sh` — atualizador transacional (equivalente ao SigUpdater.exe do Windows)

O app tem estas abas: Transcrição ao vivo, Transcrição de arquivos, Qualificação, IMEI, FFmpeg, Histórico e oitiva. Toda a lógica está em `src/sig_app.py` (~13.100 linhas, 575+ funções).

---

## 2. ESTADO ATUAL DO PROJETO (D:/Projetos/SIG Linux)

JÁ FEITO (não refazer):
- ✅ `src/sig_app.py`, `src/assistant_prompts.py`, `src/vad_worker.py` copiados do Windows e adaptados:
  - `settings_path()` usa `XDG_CONFIG_HOME` no Linux
  - `_ffmpeg()`, `_ffplay()`, `_get_ffprobe()`: buscam binário local → fallback no PATH (`which`)
  - Abertura de pastas via `xdg-open` (3 pontos)
  - Updater: `_update_script_text()` gera **bash** transacional; `_launch_prepared_update()` usa `/bin/bash sig_updater.sh` no Linux; fluxo Windows preservado em `_launch_prepared_update_windows()`
  - `required_members` do ZIP: versão Linux (`sig`, `_internal/base_library.zip`, `_internal/libpython3.11.so.1.0`, `sig_updater.sh`)
- ✅ `sig.spec` (one-dir, sem DLLs Windows, ícone assets/icon.png)
- ✅ `scripts/release.py` e `scripts/release_validation.py` adaptados (nomes sem .exe, updater = sig_updater.sh, PortAudio do sistema)
- ✅ `tests/`, `assets/`, `requirements.txt` copiados
- ✅ `APP_VERSION = "20260812_005"` (herdado do Windows — será trocado na 1ª release Linux)

PENDENTE (seu trabalho):
- ❌ `updater_linux/sig_updater.sh` — materializar o script que `_update_script_text()` gera (ver seção 7)
- ❌ `updater_linux/harness.py` — harness de teste do updater (equivalente ao `updater_v2/harness.py`)
- ❌ `scripts/updater_artifact.json` — hash/size do sig_updater.sh versionado
- ❌ `scripts/runtime_artifact.json` — fingerprint dos assets fixos (ffmpeg, ffplay, vad_deps)
- ❌ `AGENTS.md`, `README.md`, `.gitignore` específicos do Linux
- ❌ Gerar par de chaves RSA para assinatura do manifesto (release/update_private_key.pem + update_public_key.pem)
- ❌ Build e testes reais num Linux (PyInstaller não faz cross-compile; o build TEM que rodar no Linux)
- ❌ Validar se os `os.startfile` remanescentes estão todos protegidos por `if os.name == "nt"` (deve estar)
- ❌ Verificar preview de vídeo no Linux (o player MCI via ctypes é Windows-only e retorna False — conferir o fallback)

---

## 3. REGRAS PERMANENTES (NUNCA VIOLAR)

1. **Build sempre one-dir (COLLECT)**. NUNCA one-file. O `sig.spec` já usa COLLECT; não remover.
2. **`sig` + `_internal/` ficam lado a lado** na instalação.
3. **Versão consistente em 3 lugares**: `APP_VERSION` em `src/sig_app.py`, `version` em `latest.json`, nome do ZIP `YYYYMMDD_NNN.zip`. Nunca publicar com valores divergentes.
4. **Toda mudança de código exige nova versão** antes de publicar, mesmo sem mudança funcional.
5. **Chaves de API NUNCA** no código-fonte, executável ou releases.
6. **`release/update_private_key.pem` NUNCA** vai para GitHub/Drive.
7. **Nunca publicar ZIP montado de `dist` antigo** — o ZIP deve vir do clean build da execução.
8. **Gate oficial obrigatório** antes de considerar qualquer versão concluída: `tests` → `validate --warn-path` → `updater-test`.
9. **Binários grandes (ffmpeg, ffplay, vad_deps) não entram no Git** — entram no pacote full da release.
10. **Publicar pelo Google Drive via API** (pasta e IDs fornecidos pelo usuário), nunca por cópia manual de unidade montada.
11. **NÃO MEXER no código do SIG Windows** (`D:/Projetos/SIG Windows`). Este projeto é independente.
12. **Comunicação final em português** (relatórios, commits, mensagens).

---

## 4. PREPARAÇÃO DO AMBIENTE LINUX

```bash
# Python 3.11 (use pyenv ou distro). Verificar:
python3 --version        # deve ser 3.11.x

# Acessar a pasta do projeto (share SMB já montado e liberado — use o caminho
# onde smb://taguai/projetos/SIG Linux já está acessível na sua máquina)
cd "SIG Linux"
python3 -m venv .venv
source .venv/bin/activate

# Dependências do app (requirements.txt)
pip install --upgrade pip
pip install -r requirements.txt
# requirements.txt contém: Pillow, sounddevice, websocket-client, pyinstaller

# Dependências de release/validação
pip install cryptography

# Dependência de sistema (PortAudio para sounddevice)
sudo apt install -y libportaudio2   # Debian/Ubuntu; em Fedora: sudo dnf install portaudio

# Dependências VAD (externas, na pasta do pacote — NÃO no venv do build)
# No Linux, o torch é a versão linux (não windows); instalar com:
pip install --target=dist/vad_deps numpy onnxruntime silero-vad webrtcvad-wheels torch
# ATENÇÃO: sem --no-deps para evitar o problema de typing_extensions/torch
# (o Windows precisou de --no-deps + torch manual; no Linux use a instalação normal)

# FFmpeg/FFplay para o pacote (sem extensão):
sudo apt install -y ffmpeg
cp $(which ffmpeg) dist/ffmpeg
cp $(which ffplay) dist/ffplay
```

Verificar ambiente de build:
```bash
python -c "import PyInstaller; print(PyInstaller.__version__)"
python -c "import sounddevice; print('sounddevice ok')"
python -c "import websocket; print('websocket ok')"
python -c "import cryptography; print('cryptography ok')"
```

---

## 5. ORDEM OBRIGATÓRIA DE TRABALHO (SIGA SEMPRE)

### FASE A — Completar as pendências de arquivos

1. **Criar `updater_linux/sig_updater.sh`**: extrair o texto gerado por `_update_script_text()` de `src/sig_app.py` e salvar como arquivo executável (chmod +x). Método simples: rodar `python -c "import sys; sys.path.insert(0,'src'); from sig_app import SigApp; print(SigApp._update_script_text())"` e salvar a saída. **IMPORTANTE**: esse arquivo versionado é a fonte oficial do updater.
2. **Criar `updater_linux/harness.py`**: equivalente do `updater_v2/harness.py` do Windows. Função `run(updater_path, zip_path, timeout)` que:
   - Monta um diretório temporário simulando uma instalação (com sig de mentira, ffmpeg fake, etc.)
   - Copia o updater + zip para lá
   - Executa o updater apontando para a instalação temporária
   - Verifica se a instalação nova foi aplicada (arquivos novos presentes, backup rollback em caso de falha)
   - Retorna lista de mensagens PASS
3. **Criar `scripts/updater_artifact.json`**: `{"sha256": <hash do sig_updater.sh>, "source_sha256": <mesmo hash>, "size": <bytes>}` (o release.py valida os dois campos).
4. **Criar `scripts/runtime_artifact.json`**: estrutura `{"files": {"ffmpeg": {"size":..., "sha256":...}, "ffplay": {...}}, "directories": {"vad_deps": <sha256 da árvore>}}`. Calcular com os binários reais que serão distribuídos.
5. **Criar `AGENTS.md`** (espelhar o do Windows, adaptado): regras de build one-dir, versão, Drive, segurança, gates — como a seção 3 deste prompt.
6. **Criar `README.md`** e **`.gitignore`** (inspirar no Windows: __pycache__, build/, dist/, release/, *.zip, *.pem, .venv/).
7. **Gerar chaves**: `openssl genrsa -out release/update_private_key.pem 2048` + extrair pública. NUNCA commitar a privada.

### FASE B — Primeiro build e teste manual

8. **Build**: `python -m PyInstaller --noconfirm --clean --distpath dist --workpath build sig.spec`
   - Conferir `dist/sig/` (one-dir) com `sig` + `_internal/`
   - Conferir `_internal/python3.11` (libpython) presente
   - Conferir warn: `build/sig/warn-sig.txt` sem `missing module named sounddevice|websocket`
9. **Copiar assets externos** para `dist/sig/`: ffmpeg, ffplay, vad_deps/, vad_worker.py, sig_updater.sh
10. **Teste de execução**: `cd dist/sig && ./sig` — a GUI deve abrir. Fechar com o X da janela.
    - Testar aba FFmpeg → converter um áudio (subprocess ffmpeg)
    - Testar VAD Silero (dropdown VAD: Silero - 1) → deve aparecer "VAD ...ms | ...s voz" na coluna Status
    - Testar abrir pasta (botão pasta) → xdg-open
    - Testar microfone ao vivo (sounddevice/PortAudio) se houver hardware
11. **Resolver erros encontrados** (ver seção 8 de pitfalls).

### FASE C — Testes unitários

12. `python scripts/release.py tests` — deve passar 100%.

### FASE D — Validação do build

13. `python scripts/release.py validate --warn-path build/sig/warn-sig.txt`
    - Se falhar por causa de `runtime_artifact.json` ausente/incompatível, gerar o manifest correto (Fase A, item 4) e rodar de novo.

### FASE E — Teste do updater

14. `python scripts/release.py updater-test --package-zip <zip-de-teste> --updater updater_linux/sig_updater.sh`
    - Se não existir zip de teste, criar um pacote mínimo manual: pasta com `sig` (script fake que dorme 5s), `_internal/base_library.zip` (arquivo dummy), `sig_updater.sh`, e zipar.
    - O harness deve reportar "Atualização aplicada e validada".

### FASE F — Release completa (só depois de A-E passarem)

15. Definir `APP_VERSION = "YYYYMMDD_001"` (data real) em `src/sig_app.py`.
16. `python scripts/release.py release --version <APP_VERSION> --zip-file-id <ID_DO_ZIP_NO_DRIVE>`
    - O release faz: clean build isolado → valida warnings → valida layout → valida dependências congeladas → valida updater artifact → roda harness → monta ZIP → assina manifesto → valida consistência.
17. **Upload do ZIP para o Drive** — pasta `14NX28WcCAcRuCT7TM8HmSD2IF6yYUOc0` (https://drive.google.com/drive/folders/14NX28WcCAcRuCT7TM8HmSD2IF6yYUOc0), sempre via API do Google Drive, e conferir via API: tamanho, sha256, ID retornado.
18. **Atualizar `latest.json` no Drive** (mesmo arquivo, não criar duplicado), assinado, na mesma pasta `14NX28WcCAcRuCT7TM8HmSD2IF6yYUOc0`.
19. **Verificação pós-publicação**:
    - O ZIP baixado tem o tamanho/sha256 do manifesto.
    - Instalação limpa: descompactar o ZIP num diretório novo, rodar `./sig`, conferir "Sobre" mostra a versão certa.
    - Se houver instalação anterior: abrir o app, "Verificar Atualizações" → deve oferecer a nova versão; instalar → conferir `updater.log` com a linha **"Atualização aplicada e validada"** (não considerar concluído só com "iniciado").

---

## 6. CHECKLIST DE VALIDAÇÃO (rodar SEMPRE antes de concluir qualquer tarefa)

- [ ] `python -m py_compile src/sig_app.py src/vad_worker.py scripts/release.py scripts/release_validation.py`
- [ ] `python scripts/release.py tests` → 100% PASS
- [ ] Build one-dir limpo gerado pelo release (não de dist antigo)
- [ ] `warn-sig.txt` sem avisos críticos (sounddevice/websocket)
- [ ] Pacote contém: sig, _internal/, ffmpeg, ffplay, vad_deps/, vad_worker.py, sig_updater.sh
- [ ] `sig` inicia e GUI abre
- [ ] Conversão FFmpeg funciona (gera WAV 16kHz mono 16-bit)
- [ ] VAD Silero e WebRTC funcionam (status mostra tempo/segundos)
- [ ] `xdg-open` abre pastas
- [ ] Updater: harness PASS + log com "Atualização aplicada e validada"
- [ ] Manifesto assinado válido (verificar com a chave pública)
- [ ] Versão consistente: APP_VERSION == latest.json.version == nome do ZIP
- [ ] `Sobre` mostra a versão publicada
- [ ] App atualizado NÃO volta a oferecer a mesma versão imediatamente
- [ ] Nenhuma chave privada ou API key no repositório

---

## 7. O SCRIPT DO UPDATER (referência — o que _update_script_text() gera)

O updater bash recebe `--zip <path> --target <dir> --pid <pid> --log <path>` e faz:
1. Loga início; resolve o diretório de instalação subindo até achar `ffmpeg`/`ffplay`/`vad_deps` (máx 6 níveis).
2. Aguarda o PID do SIG fechar (deadline 120s, sleep 0.25).
3. Cria backup em `/tmp/sig_backup_XXXXXX` e staging `$(dirname zip)/staging`.
4. Valida o ZIP via `python3 -m zipfile` (testzip + membros obrigatórios: sig, _internal/base_library.zip, sig_updater.sh).
5. Extrai staging (unzip ou python3 -m zipfile -e).
6. Aplica: substitui `_internal/` inteiro; copia arquivos individuais com backup (rollback em falha).
7. `chmod +x sig sig_updater.sh`.
8. Inicia o sig novo e valida que ficou vivo 5s; se falhar → rollback + relança o sig antigo + exit 1.
9. Sucesso → "Atualização aplicada e validada", remove temporários, exit 0.

Ao materializar o arquivo, o conteúdo deve ser EXATAMENTE o retornado por `_update_script_text()`.

---

## 8. PITFALLS CONHECIDOS (já enfrentados no Windows — evitar no Linux)

1. **PyInstaller não faz cross-compile**: o build Linux só funciona num Linux. Nunca tentar gerar o executável Linux no Windows.
2. **one-file quebra em algumas máquinas**: SEMPRE one-dir (COLLECT). Erro "Failed to load Python DLL ... _MEI..." indica one-file.
3. **VAD dentro do exe falha**: o PyInstaller não inclui toda a stdlib (ex.: `timeit`) e o torch quebra. Por isso o VAD roda como **subprocesso** `python3 vad_worker.py` usando `vad_deps/` externo. Não tentar importar silero/torch dentro do exe.
4. **vad_deps precisa de torch**: silero-vad faz `import torch` incondicionalmente. Instalar com dependências completas.
5. **sounddevice precisa de libportaudio2** no sistema; sem isso o app abre mas microfone falha.
6. **MCI/winmm não existe no Linux**: o `EmbeddedMediaPlayer` retorna False e o app usa fallback. Testar preview de vídeo; se o fallback não existir, implementar (ex.: ffplay subprocess em janela própria ou imagem estática).
7. **`os.startfile` não existe no Linux** — já trocado por xdg-open; se aparecer algum novo, usar `subprocess.Popen(["xdg-open", path])`.
8. **`subprocess.CREATE_NO_WINDOW` não existe no Linux** — usar `creationflags=0` (já padronizado via `if os.name == "nt"`).
9. **Nomes de binários**: no Linux é `ffmpeg`/`ffplay`/`ffprobe` sem extensão; `_ffmpeg()`/`_ffplay()` já fazem fallback no PATH.
10. **CArchiveReader funciona igual no Linux** para ler a versão congelada (frozen_app_version).
11. **ZIP com caminhos inválidos**: o validador rejeita `..`, absolutos, duplicados, pastas `g`/`dist` — manter a estrutura limpa ao montar o pacote.
12. **Primeiro load do modelo Silero é mais lento** (~300ms) — normal; depois ~150ms.
13. **Cancelar transcrição demora se servidor não responde**: o timeout das conexões de transcrição é 1h (60*60). Para cancelamento rápido, considerar reduzir ou fechar conexões no cancel (uploader.cancel() já fecha).
14. **WSL**: não usar WSL para o build se o alvo for desktop Linux puro (dependências de som/Tk podem falhar). Preferir máquina Linux real.

---

## 9. REGRAS DE GIT

- Commits em português, mensagens claras.
- NUNCA commitar: `dist/`, `build/`, `release/` (zips, chaves, latest.json), `.venv/`, `*.zip`, `*.pem`, `settings.json`, `vad_deps/`, binários grandes.
- Versionar: `src/`, `assets/` (imagens pequenas), `scripts/` (com os patch_* que documentam a migração), `tests/`, `updater_linux/`, `sig.spec`, `AGENTS.md`, `README.md`, `requirements.txt`, `.gitignore`.
- A primeira release Linux usa APP_VERSION novo (nunca reutilizar versão do Windows).

---

## 10. ENTREGA ESPERADA AO FINAL

1. Projeto compilando e validado no Linux com TODOS os gates PASS.
2. `AGENTS.md` atualizado com as regras finais.
3. Pacote full pronto para publicação (ZIP + latest.json assinado + upload Drive conferido).
4. Relatório final em português com: comandos executados, resultados de cada gate, versão publicada, ID do ZIP no Drive, e qualquer pendência residual.
5. Se algo falhar sem solução clara, reportar com o log/erro exato em vez de contornar silenciosamente.
