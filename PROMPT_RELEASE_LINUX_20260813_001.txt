# PROMPTO — Concluir build e publicação da release 20260813_001 do SIG Linux

> Este é o roteiro exato para concluir a release **20260813_001** do SIG Linux.
> Siga os passos na ordem. Não pule gate. Não improvise versões ou chaves.

---

## 1. Contexto (leia antes de agir)

O SIG Linux foi sincronizado com o SIG Windows em 13/08/2026 (commits
`5d15624`, `c240c37` e `0dd921d` já estão em `main` do repositório
`github.com/spigknot/SIG-Linux`). O que mudou:

- `src/sig_app.py` portado do Windows (14,7k linhas): geração de documentos
  Word (.docx) a partir dos modelos em `modelos/`, prompts externos em
  `prompts/`, editor ao vivo de qualificação, status do assistente.
- Novo atualizador endurecido: `updater_linux/sig_updater.py` (port direto do
  `updater_v2/updater.py` do Windows — validação completa de ZIP, lock
  exclusivo `fcntl`, journal transacional, rollback, espera por processos via
  `/proc`) e `updater_linux/sig_updater.sh` virou **launcher fino** que faz
  `exec python3 sig_updater.py "$@"`.
- Gates de release atualizados: `prompts/` e `modelos/` passaram a fazer parte
  do pacote e dos arquivos obrigatórios; o artifact do updater agora valida
  **dois** hashes (`sig_updater.sh` e `sig_updater.py`).
- Novo script `scripts/sign_release_manifest.py` para assinar o manifesto
  **após** o upload do ZIP (sem rebuild — ver passo 6).

Estado atual das coisas:

| Item | Estado |
|---|---|
| Código no GitHub | ✅ commits `5d15624` + `c240c37` + `0dd921d` em `main` |
| Release no GitHub | ✅ `v20260813_001` **já criada** (com `install.sh` anexado) — falta o ZIP |
| `APP_VERSION` em `src/sig_app.py` | ⚠️ ainda `"20260812_002"` — **você deve atualizar para `"20260813_001"`** |
| Manifesto no Drive | ⚠️ aponta para `20260812_002` — você vai publicar o novo |
| Pacote full da 001 | ❌ não existe ainda — é o seu trabalho |

Valores fixos (NÃO alterar):

- Pasta do Drive: `14NX28WcCAcRuCT7TM8HmSD2IF6yYUOc0`
- ID do manifesto no Drive (`UPDATE_MANIFEST_FILE_ID` no código): `14qU9b4wbyu7_6hAOvip6qhSG91E45BJ3`
- `UPDATE_PUBLIC_KEY_E` / `UPDATE_PUBLIC_KEY_N` em `src/sig_app.py`: **preservados
  do Linux** — a chave privada que assinou a release `20260812_002` continua
  válida. **NUNCA gerar chave nova.** A chave privada deve existir em
  `release/update_private_key.pem` na sua máquina (a mesma de antes).
- Hashes do artifact do updater (`scripts/updater_artifact.json`):
  - `sig_updater.sh`: sha256 `8c9747ff1482e2f8cff4a8588b72d074283d3e9995b377809dcc4c0b117be6b8`, 375 bytes
  - `sig_updater.py`: sha256 `c5e579039fe6ea4bc4c74275da8b29f23110a0994c005e9cdc9cff0290b103b2`, 28927 bytes

---

## 2. Ambiente esperado

- Máquina **Linux real** (PyInstaller não faz cross-compile; WSL não serve).
- Python 3.11 com `pyinstaller`, `sounddevice`, `websocket-client`,
  `google-api-python-client`, `google-auth-oauthlib`, `cryptography`
  no mesmo ambiente (venv do projeto).
- `libportaudio2` do sistema (ou o `sitecustomize.py` do venv desta máquina
  apontando para o PortAudio local extraído do .deb).
- `gh` CLI autenticado (usado na release anterior): confira com
  `gh auth status`. Se não estiver, autentique antes do passo 8.
- `ffmpeg`/`ffplay` Linux e `dist/vad_deps/` prontos em `dist/` (não mexer
  neles; são o `--runtime-root` padrão).
- `unzip`, `curl`, `python3` no sistema.

Verificações rápidas antes de começar:

```bash
python3 -c "import sounddevice, websocket, PyInstaller" && echo AMBIENTE_OK
gh auth status
test -f release/update_private_key.pem && echo CHAVE_OK || echo "FALTA A CHAVE PRIVADA — resolva antes"
test -f release/credentials.json && echo CRED_OK
test -f release/token_drive.json && echo TOKEN_OK
```

Se `FALTA A CHAVE PRIVADA`: **pare e avise o usuário**. Não gere chave nova —
isso invalidaria a verificação de assinatura embutida no app publicado.

---

## 3. Passo 0 — Sincronizar o código e atualizar APP_VERSION

```bash
cd <pasta-do-projeto>            # via clone git ou a pasta do SMB já vinculada
git fetch origin && git checkout main && git pull --ff-only origin main
git log --oneline -5             # deve mostrar 0dd921d no topo
```

Atualize **somente** a linha 51 de `src/sig_app.py`:

```python
APP_VERSION = "20260813_001"
```

Confirme que o valor em `src/sig_app.py` bate com o restante (não toque em
`UPDATE_MANIFEST_FILE_ID`, `UPDATE_PUBLIC_KEY_E`, `UPDATE_PUBLIC_KEY_N`):

```bash
grep -n "^APP_VERSION\|^UPDATE_MANIFEST_FILE_ID" src/sig_app.py
python3 -c "import sys; sys.path.insert(0,'scripts'); from release import read_app_version; print(read_app_version('src/sig_app.py'))"
```

Comite e envie:

```bash
git add src/sig_app.py
git commit -m "APP_VERSION 20260813_001"
git push origin main
```

---

## 4. Passo 1 — Gates obrigatórios (nesta ordem)

Todos devem terminar sem erro. Se algum falhar, corrija e rode tudo de novo
desde o início.

```bash
# 4.1 testes unitários (27 testes esperados)
python3 scripts/release.py tests

# 4.2 validação do estado atual (usa dist/ e o manifesto local)
python3 scripts/release.py validate --warn-path build/sig/warn-sig.txt

# 4.3 harness do atualizador em pasta temporária (exercita o updater REAL:
#     rejeição de zips inválidos, processo ativo, sucesso com resolução de
#     destino, rollback por falha de inicialização)
python3 scripts/release.py updater-test
```

Observações:

- O `validate` compara o hash de `dist/` (ffmpeg, ffplay, vad_deps) com
  `scripts/runtime_artifact.json`. Se falhar com "conteúdo antigo ou
  alterado", **investigue primeiro**: se o conteúdo de `dist/` mudou de
  propósito (ex.: atualizou o ffmpeg), regenere o fingerprint com
  `python3 -c "import sys,json; sys.path.insert(0,'scripts'); from release_validation import runtime_asset_fingerprint; from pathlib import Path; print(json.dumps(runtime_asset_fingerprint(Path('dist')), indent=2))" > scripts/runtime_artifact.json`,
  **revise o diff do json com cuidado** e comite. Nunca regenere para "fazer
  passar" sem entender o que mudou.
- O `updater-test` precisa de `/bin/bash` e `python3` no PATH. Ele usa
  `updater_linux/sig_updater.sh` + `updater_linux/sig_updater.py` e um pacote
  mínimo gerado sob demanda. Saída esperada: 4 linhas `PASS:`.
- Se o `tests` falhar no `test_updater.py` (harness), rode com `-v` para ver
  qual cenário quebrou: `python3 -m unittest updater_linux.test_updater -v`.

---

## 5. Passo 2 — Build da release (clean build isolado)

```bash
python3 scripts/release.py release --version 20260813_001
```

Este comando, em sequência e sem intervenção:

1. Confere que `APP_VERSION` == `20260813_001` e que é posterior à versão do
   `release/latest.json` local (não precisa de `--allow-same`).
2. Valida os hashes do updater contra `scripts/updater_artifact.json`.
3. Faz **clean build** do PyInstaller em pasta temporária (`--clean`, workpath
   e distpath isolados; o `dist/` real não é tocado).
4. Monta o pacote em `release/generated/20260813_001/package/` com
   `_internal`, `prompts/`, `modelos/`, `vad_worker.py`, `ffmpeg`, `ffplay`,
   `vad_deps/`, `sig_updater.sh` (chmod +x) e `sig_updater.py`.
5. Roda os gates internos: warnings críticos do PyInstaller, layout do pacote
   (inclui `prompts/` e `modelos/`), dependências congeladas
   (PortAudio/sounddevice/websocket), artifact do updater (duplo hash),
   `build-info.json`, versão congelada == `20260813_001`.
6. Gera `release/generated/20260813_001/20260813_001.zip` (pacote full,
   ~350 MB) e **roda o harness do updater contra esse ZIP exato**.
7. Gera `release/generated/20260813_001/latest.draft.json` (rascunho do
   manifesto, sem assinatura, `zip_file_id = PENDING_DRIVE_UPLOAD`).

Saída esperada no fim:

```
PASS: build limpo e pacote validado: <...>/20260813_001.zip
Manifesto rascunho: <...>/latest.draft.json
```

Confira o tamanho e o hash do ZIP (vai precisar do hash nos passos 6 e 7):

```bash
ls -la release/generated/20260813_001/
sha256sum release/generated/20260813_001/20260813_001.zip
```

**Atenção:** o build não é bit-reprodutível (uuid + timestamp no
build-info.json). Por isso o manifesto é assinado **depois** do upload (passo
6), usando o ZIP já gerado — nunca rode `release` de novo para a mesma versão
(o diretório de saída não pode estar ocupado e o hash mudaria).

---

## 6. Passo 3 — Upload do ZIP ao Drive (API, nunca por SMB)

```bash
# garanta o token do Drive (renova/gera se precisar)
python3 scripts/drive_upload.py auth

# upload do pacote (imprime o ID no final)
python3 scripts/drive_upload.py upload release/generated/20260813_001/20260813_001.zip
```

Anote o **ID do arquivo** impresso na última linha (algo como `ZIP_ID`).
Confira pela API com o ID e o sha256 do passo 5:

```bash
python3 scripts/drive_upload.py verify <ZIP_ID> <SHA256_DO_ZIP> --name 20260813_001.zip
```

Saída esperada: `VERIFY OK: sha256=<...>`.

> **Fallback autorizado** (apenas se a API falhar de verdade): copiar o ZIP
> para `smb://taguai/meu drive/Updater/Sig/Linux` — ela espelha a pasta de
> updates do Drive. Sempre tentar a API primeiro e avisar o usuário quando
> usar o fallback.

---

## 7. Passo 4 — Assinar o manifesto (SEM rebuild)

Use o script novo (já está no repositório):

```bash
python3 scripts/sign_release_manifest.py 20260813_001 <ZIP_ID>
```

O script:

1. Lê `release/generated/20260813_001/latest.draft.json` (versão, nome,
   sha256 e tamanho do ZIP **já enviado**).
2. Injeta o `zip_file_id`.
3. Assina com `release/update_private_key.pem` (PKCS1v15/SHA-256) e grava
   `release/generated/20260813_001/latest.json`.
4. Valida o formato e a assinatura contra a chave pública embutida em
   `src/sig_app.py`.

Saída esperada:

```
OK: manifesto assinado e validado: <...>/latest.json
  version=20260813_001 zip=20260813_001.zip
  sha256=<...>
  size=<...>
```

---

## 8. Passo 5 — Publicar o manifesto no Drive

```bash
python3 scripts/drive_upload.py publish release/generated/20260813_001/latest.json
```

O comando atualiza o `latest.json` **existente** na pasta do Drive (não cria
duplicado) e confere o tamanho pela API. Saída esperada:
`MANIFESTO atualizado: id=... size=...`.

Verifique o conteúdo publicado (deve apontar para o ZIP novo):

```bash
curl -fsSL "https://drive.usercontent.google.com/download?id=14qU9b4wbyu7_6hAOvip6qhSG91E45BJ3&export=download&confirm=t" | python3 -m json.tool | head -20
```

Confira que `version`, `zip_name`, `sha256`, `size` e `zip_file_id` batem com
o `latest.json` assinado e com o ZIP enviado.

---

## 9. Passo 6 — Verificação pós-publicação (obrigatória)

```bash
# 9.1 ZIP íntegro na API (tamanho + sha256 rebaixado)
python3 scripts/drive_upload.py verify <ZIP_ID> <SHA256_DO_ZIP> --name 20260813_001.zip

# 9.2 manifesto íntegro na API
python3 scripts/drive_upload.py verify 14qU9b4wbyu7_6hAOvip6qhSG91E45BJ3 <SHA256_DO_LATEST_JSON> --name latest.json

# 9.3 o app publicado ainda valida o manifesto (mesma chave pública)
python3 - <<'EOF'
import sys
sys.path.insert(0, "scripts")
from release import read_manifest, validate_manifest_shape, validate_manifest_signature
m = read_manifest("release/generated/20260813_001/latest.json")
validate_manifest_shape(m)
validate_manifest_signature(m, "src/sig_app.py")
print("ASSINATURA OK")
EOF
```

---

## 10. Passo 7 — Anexar o pacote à release do GitHub (já criada)

A release `v20260813_001` já existe com as notas e o `install.sh`. **Não criar
outra release.** Apenas anexe o ZIP:

```bash
gh release upload v20260813_001 release/generated/20260813_001/20260813_001.zip --repo spigknot/SIG-Linux
gh release view v20260813_001 --repo spigknot/SIG-Linux
```

Confira que a release lista dois assets: `install.sh` e `20260813_001.zip`.

---

## 11. Passo 8 — Teste de instalação limpa (do zero, como um usuário novo)

Sem tocar na instalação real (`~/.local/share/sig`), teste numa pasta
temporária:

```bash
SIG_INSTALL_DIR=/tmp/sig_install_test SIG_BIN_DIR=/tmp/sig_install_test/bin \
  curl -fsSL https://raw.githubusercontent.com/spigknot/SIG-Linux/main/install.sh | bash
```

Esperado:

- Baixa o manifesto e o ZIP **novos** (versão `20260813_001`).
- Confere `sha256` e tamanho.
- Instala em `/tmp/sig_install_test`.
- Cria o launcher e o `.desktop`.

Depois abra o app instalado:

```bash
/tmp/sig_install_test/sig &
```

Confirme visualmente em **Sobre** que a versão exibida é `20260813_001`.
Feche o app e remova o teste: `rm -rf /tmp/sig_install_test`.

## 12. Passo 9 — Teste de atualização incremental (da 002 para a 001)

Se houver uma instalação real da versão `20260812_002` disponível na máquina
(cuidado para não mexer na instalação de produção sem avisar o usuário),
verifique o caminho completo de update:

1. Abrir o SIG antigo (002) — ele deve detectar a atualização disponível
   (manifesto novo).
2. Aceitar a atualização e aguardar o reinício.
3. Conferir no log do atualizador
   (`~/.local/share/sig-updater.log` ou o caminho de `updater.log` do app) a
   linha **`Atualização aplicada e validada.`** — não considerar concluído só
   com `SigUpdaterV2 iniciado.`.
4. Abrir o SIG e conferir a versão `20260813_001` em Sobre.
5. Conferir que ele **não** volta a oferecer a mesma versão.

Se não houver instalação 002 segura para testar, registre isso no seu relatório
final (o harness dos passos 4.3 e 5.6 já cobre o mecanismo).

---

## 13. Passo 10 — Commit final dos artefatos versionáveis

Depois de tudo publicado e verificado:

```bash
git status --short
```

Devem entrar no commit final (se ainda não estiverem):

- `src/sig_app.py` (APP_VERSION)
- `release-notes-20260813_001.md` (se você editar as notas, ex.: remover o
  aviso de "pacote pendente" e registrar o sha256 do ZIP)

**Nunca commitar**: `release/update_private_key.pem`,
`release/credentials.json`, `release/token_drive.json`, `dist/`,
`release/generated/` (todos já ignorados — confirme com `git check-ignore -v <arquivo>`
antes de forçar qualquer coisa).

```bash
git add -A && git status --short && git diff --cached --stat
git commit -m "Publica release 20260813_001 (pacote no Drive e no GitHub)"
git push origin main
```

---

## 14. Checklist de aceite (responda item a item no relatório final)

- [ ] `APP_VERSION = "20260813_001"` commitado em `main`
- [ ] Gates: `tests`, `validate`, `updater-test` — todos PASS
- [ ] `release.py release --version 20260813_001` — build limpo + harness no ZIP real PASS
- [ ] ZIP no Drive com tamanho e sha256 conferidos pela API
- [ ] `latest.json` assinado publicado no Drive (ID `14qU9b4wbyu7_6hAOvip6qhSG91E45BJ3`) apontando para o ZIP novo
- [ ] Assinatura do manifesto validada contra a chave pública do app
- [ ] `20260813_001.zip` anexado à release `v20260813_001` do GitHub
- [ ] Instalação limpa via `install.sh` terminou na versão `20260813_001`
- [ ] (se aplicável) Atualização incremental 002→001 confirmada com
      `Atualização aplicada e validada.` no log
- [ ] Nada sensível commitado (`git status` limpo e chaves fora do repo)

---

## 15. Regras duras (nunca, em hipótese alguma)

1. **Nunca** usar `--allow-same` para publicar (existe só para smoke test local).
2. **Nunca** gerar chave privada/pública nova — a pública embutida no app não muda.
3. **Nunca** publicar pelo SMB; API primeiro, fallback autorizado só com aviso.
4. **Nunca** commitar `update_private_key.pem`, `credentials.json`,
   `token_drive.json`, `dist/`, `release/generated/`.
5. **Nunca** criar um `latest.json` duplicado no Drive — sempre atualizar o existente.
6. **Nunca** montar o ZIP incremental "na mão" a partir de `dist/` — o `sig`
   precisa vir do clean build daquela execução.
7. **Nunca** rodar `release.py release` duas vezes para a mesma versão — a
   assinatura usa o ZIP já gerado via `sign_release_manifest.py`.
8. **Nunca** alterar `UPDATE_MANIFEST_FILE_ID`, `UPDATE_PUBLIC_KEY_E/N` ou os
   hashes de `scripts/updater_artifact.json` sem mudar o updater de forma
   deliberada (e atualizar os dois juntos).
9. Se algo fugir deste roteiro: **pare, registre o desvio no relatório e
   avise o usuário** em vez de improvisar.
