# SIG Linux 20260813_001

- Código sincronizado com o SIG Windows (14,7k linhas), com adaptações Linux.
- Geração de documentos de ocorrência (declarações e depoimento) a partir dos modelos Word editáveis em `modelos/`.
- Prompts externalizados em `prompts/` (um `.txt` por prompt), editáveis sem recompilar.
- Exportação do documento para PDF via LibreOffice headless; cópia do texto para o clipboard via xclip/wl-copy.
- Atualizador endurecido: `updater_linux/sig_updater.py` (port direto do `updater_v2` do Windows) com validação completa do ZIP, lock exclusivo, journal transacional, rollback automático e espera por todos os processos do SIG; `sig_updater.sh` é agora o launcher fino.
- Gates de release atualizados: prompts/modelos no pacote, hash duplo do updater (`.sh` e `.py`), 27 testes unitários.

> Pacote full: gerado na máquina Linux pelo fluxo oficial (`python scripts/release.py release --version <APP_VERSION> --zip-file-id <ID_DO_DRIVE>`). O ZIP é anexado a esta release após o build.
