# Instruções permanentes do SIG Linux

Estas regras são obrigatórias para futuras alterações, compilações e publicações.

## Código-fonte e prompts

- Todos os prompts editáveis ficam em `prompts/`, um arquivo `.txt` por prompt:
  `historico.txt`, `oitiva_system.txt`, `oitiva_user.txt`, `partes_system.txt`,
  `quaficacao_system.txt` e `qualificacao_user.txt`.
- `src/assistant_prompts.py` deve permanecer apenas como carregador e montador das
  partes variáveis. Não voltar a colocar os textos completos dos prompts nesse módulo.
- O build empacota uma cópia em `_internal/prompts` e o pacote full também leva
  `prompts/` ao lado do `sig`; a pasta externa tem prioridade para permitir edição
  sem recompilação.
- Os modelos Word editáveis ficam em `modelos/`, no mesmo nível de `prompts/`:
  `modelo_declaracoes.docx` e `modelo_depoimento.docx`. O build deve sempre
  empacotar ambos em `_internal/modelos`; em execução, a cópia externa ao lado
  do SIG tem prioridade e nunca deve ser sobrescrita se já existir.
- Geração de documentos: no Windows a cópia rica (RTF/HTML) e o PDF usam o
  Microsoft Word; no Linux o PDF usa o LibreOffice headless (`soffice
  --headless --convert-to pdf`) e a cópia leva o texto puro do DOCX para o
  clipboard via `xclip`/`wl-copy`. Detectar as ferramentas em runtime e dar
  erro amigável quando ausentes (nunca falhar em silêncio).

## Build do aplicativo

- O SIG Linux deve ser compilado em modo **onedir** (COLLECT).
- Nunca voltar para one-file/one-exe. O modo one-file extrai para `_MEI...` e já causou falhas em outros computadores.
- O executável final deve ficar ao lado da pasta `_internal`:
  - `sig`
  - `_internal/libpython3.11.so.1.0`
- O `sig.spec` já usa `COLLECT`. Não remover essa etapa.
- Antes de cada publicação, atualizar `APP_VERSION` em `src/sig_app.py` para a mesma versão do ZIP e do `latest.json`.
- O PyInstaller, o `sounddevice` e o `websocket-client` devem estar no mesmo ambiente Python (venv do projeto). Antes de compilar, confirmar:
  - `python -c "import sounddevice"`
  - `python -c "import websocket"`
- O `sounddevice` no Linux carrega o PortAudio do **sistema** (`libportaudio.so.2`, pacote `libportaudio2`). Sem ele o app abre, mas o microfone falha.
- Testar o executável abrindo por pelo menos alguns segundos e confirmar a existência de `_internal/libpython3.11.so.1.0`.

## Pacote completo

Uma instalação nova precisa conter, na mesma pasta:

- `sig`
- `_internal/`
- `sig_updater.sh` (launcher fino)
- `sig_updater.py` (lógica transacional do updater)
- `ffmpeg`
- `ffplay`
- `vad_deps/`
- `vad_worker.py`
- `prompts/`
- `modelos/`

Não colocar esses binários grandes no histórico normal do Git. Publicar o pacote completo como ZIP da release.

## Atualização incremental pelo Drive

- Publicar exclusivamente pela API do Google Drive. Não copiar nem sincronizar o pacote pela unidade montada do SMB.
- **Fallback autorizado** (quando a API falhar): copiar para a pasta montada `smb://taguai/meu drive/Updater/Sig/Linux` — ela espelha a pasta de updates do Drive (sync no servidor) e propaga os arquivos para o Drive. Sempre tentar a API primeiro.
- Pasta Drive: `14NX28WcCAcRuCT7TM8HmSD2IF6yYUOc0`
- Manifesto: `latest.json` (mesmo arquivo, atualizado pela API; nunca criar duplicado)
- O ZIP incremental deve usar a próxima versão `YYYYMMDD_NNN.zip`.
- A versão precisa ser consistente em três lugares: `APP_VERSION` em `src/sig_app.py`, `version` em `latest.json` e o nome do ZIP. Nunca publicar quando esses valores forem diferentes.
- Mesmo uma compilação sem mudança funcional precisa receber uma nova versão interna antes de ser publicada.
- Para uma instalação onedir, o ZIP incremental deve conter na raiz `sig` e `_internal/` juntos.
- Nunca publicar um ZIP contendo apenas um `sig` quando a instalação de destino for onedir.
- O ZIP deve ser montado a partir da compilação recém-gerada, nunca de um pacote antigo que já estava em `dist`.
- O manifesto deve conter `schema`, `version`, `zip_file_id`, `zip_name`, `sha256`, `size`, `created_at` e `signature`.
- Assinar usando a chave privada local (`release/update_private_key.pem`); a verificação usa `UPDATE_PUBLIC_KEY_E`/`UPDATE_PUBLIC_KEY_N` embutidos em `src/sig_app.py`.
- Nunca enviar `release/update_private_key.pem` ao GitHub ou ao Drive.
- Depois do upload, conferir o ZIP e o `latest.json` pela API usando os IDs retornados.

## Segurança

- Nunca gravar chaves de API no código-fonte, no executável ou em releases.
- Não publicar arquivos de configuração, chaves privadas, `settings.json`, caches ou pastas temporárias.
- Se uma chave aparecer no histórico público, avisar o usuário para revogá-la e rotacioná-la.

## Verificação antes de concluir

1. Confirmar que o SIG não está em execução antes de substituir `dist/sig` ou `_internal`.
2. Compilar em onedir.
3. Testar a abertura do executável.
4. Conferir `libpython3.11.so.1.0`, PortAudio e `sounddevice` no pacote.
5. Conferir a estrutura interna do ZIP.
6. Atualizar o manifesto e validar a assinatura.
7. Verificar no Drive a versão, o tamanho e o SHA-256 publicados.
8. Conferir no log do updater a linha `Atualização aplicada e validada.`; não considerar concluído apenas porque apareceu `SigUpdaterV2 iniciado.`.
9. Abrir o SIG atualizado e conferir em Sobre que a versão exibida é a mesma do manifesto. Se a versão antiga continuar aparecendo, o `APP_VERSION` não foi atualizado.
10. Confirmar que o SIG atualizado não volta a oferecer a mesma versão imediatamente.

## Diagnóstico do updater

- O `sig_updater.sh` (launcher) e o `sig_updater.py` (lógica) devem permanecer ao lado do SIG numa instalação completa.
- Erro `Failed to load Python DLL ... _MEI...` indica distribuição one-file ou falha na extração temporária; reconstruir em onedir e incluir `_internal` no pacote.
- Se o log disser que `_internal` e `sig` foram instalados, mas a versão não mudou, verificar primeiro `APP_VERSION` antes de culpar a cópia.
- Se o log parar em `aguardando validação`, aguardar a linha final de validação e conferir o processo; não publicar outra tentativa sem diagnosticar.
- Testar o executável instalado com o diretório de trabalho apontando para a pasta que contém `ffmpeg`, `ffplay`, `vad_deps` e `_internal`.
- `updater_linux/sig_updater.py` é o port direto do `updater_v2/updater.py` do Windows. Toda melhoria de segurança feita lá DEVE ser replicada aqui (e vice-versa).
- O updater é transacional e valida antes de tocar a instalação:
  - ZIP: CRC de cada membro (`testzip`), sem criptografia, sem symlinks, sem caminhos absolutos/`..`/`.`/`\x00`/`:`, sem nomes duplicados, sem `g`/`dist`/`_MEI`, topologia consistente (arquivo usado como diretório), top-level restrito a uma allowlist, limites de entradas (10k), de membro (1 GiB) e total (4 GiB), membros obrigatórios e `build-info.json` com versão válida.
  - Instalação alvo: componentes obrigatórios e árvore sem symlinks/`g`/`_MEI`.
  - Lock exclusivo por instalação (`.sig.sig-update.lock`, `fcntl` no Linux).
  - Espera o PID do SIG e TODOS os processos com o mesmo executável (via `/proc/*/exe`) encerrarem.
  - Journal transacional com fases (`prepared → old-moved → new-moved → validated`) e backup; transações interrompidas são recuperadas ou revertidas na próxima execução.
  - Troca atômica por componente (rename), validação da árvore instalada, inicialização do SIG novo confirmada e rollback automático com relançamento da versão anterior em falha.
- O `sig_updater.sh` é o launcher fino gerado por `_update_script_text()` em `src/sig_app.py` (fonte oficial) e materializado em `updater_linux/sig_updater.sh` por `scripts/materialize_updater.py`. O `updater_linux/sig_updater.py` é a fonte oficial da lógica. Toda alteração DEVE atualizar `scripts/updater_artifact.json` (hash do `.sh` e do `.py`).

## Gate oficial de build e release

- Nenhuma versão pode ser considerada concluída ou publicável sem passar pelo comando oficial em `scripts/release.py`.
- A sequência mínima obrigatória, executada no mesmo Python que contém PyInstaller, é:
  `python scripts/release.py tests`
  `python scripts/release.py validate --warn-path build/sig/warn-sig.txt`
  `python scripts/release.py updater-test --package-zip <zip-de-teste>`
- Para gerar uma release, usar somente:
  `python scripts/release.py release --version <APP_VERSION> --zip-file-id <ID_DO_ZIP_NO_DRIVE>`
- Esse comando faz clean build isolado, verifica warnings críticos, inspeciona o executável congelado, valida layout/dependências, testa o updater real em pasta temporária, cria o ZIP e assina o manifesto. Se uma etapa falhar, a release não é aprovada.
- `--allow-same` existe somente para smoke test local da versão atual e nunca deve ser usado para publicar.
- O ZIP nunca deve ser criado manualmente a partir de `dist`. O `sig` precisa vir do clean build desta execução; os assets externos somente podem vir de um `--runtime-root` explicitamente escolhido e passam pelo gate de layout e pelo hash conhecido do `sig_updater.sh` (`scripts/updater_artifact.json`).
- Os assets fixos de runtime (`ffmpeg`, `ffplay`, `vad_deps/`) têm fingerprint versionado em `scripts/runtime_artifact.json`.
- O harness de teste do updater vive em `updater_linux/harness.py` e é executado tanto pelo `updater-test` quanto dentro do `release`.

## Ambiente de build

- O build só funciona em Linux real (PyInstaller não faz cross-compile). Não usar WSL como alvo de desktop Linux puro.
- Dependências de sistema: `ffmpeg`, `libportaudio2`, `unzip`, `python3` (3.11).
- `vad_deps/` é externo ao executável: `pip install --target dist/vad_deps numpy onnxruntime silero-vad webrtcvad-wheels torch`. O VAD roda como subprocesso `python3 vad_worker.py` usando `vad_deps/` — nunca importar silero/torch dentro do exe.
- Esta máquina de build usa `~/.venvs`/venv local do projeto; o `sitecustomize.py` do venv aponta para um PortAudio local extraído de `.deb` (sem sudo) apenas nesta máquina — máquinas normais usam `libportaudio2` do sistema.
