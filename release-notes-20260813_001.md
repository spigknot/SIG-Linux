# SIG Linux 20260813_001

- Código sincronizado com o SIG Windows (14,7k linhas), com adaptações Linux.
- Geração de documentos de ocorrência (declarações e depoimento) a partir dos modelos Word editáveis em `modelos/`.
- Prompts externalizados em `prompts/` (um `.txt` por prompt), editáveis sem recompilar.
- Exportação do documento para PDF via LibreOffice headless; cópia do texto para o clipboard via xclip/wl-copy.
- Atualizador endurecido: `updater_linux/sig_updater.py` (port direto do `updater_v2` do Windows) com validação completa do ZIP, lock exclusivo, journal transacional, rollback automático e espera por todos os processos do SIG; `sig_updater.sh` é agora o launcher fino.
- Gates de release atualizados: prompts/modelos no pacote, hash duplo do updater (`.sh` e `.py`), 27 testes unitários.

> Pacote full publicado no GitHub Releases (asset `20260813_001.zip`):
> 365.142.521 bytes, sha256 `c2bd76d5cb46c390bdd8c40667ea56aa20bd36dfb04ba282042420c7fd8cdc3f`
> (digest conferido pelo próprio GitHub).
>
> Update incremental publicada no Google Drive (pasta 14NX28WcCAcRuCT7TM8HmSD2IF6yYUOc0):
> `20260813_001-incremental.zip` — 26.551.129 bytes,
> sha256 `e63031955e392971db71be435a58c14e303c33e0e86fd266d1bcab4a17f26c0a`,
> ID `15Fi2RiouiUXiezAVC3tGm8cP9Cb8G79V`. O `latest.json` assinado (ID
> `14qU9b4wbyu7_6hAOvip6qhSG91E45BJ3`) aponta para a incremental.
