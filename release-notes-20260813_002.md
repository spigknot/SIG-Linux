# SIG Linux 20260813_002

- Corrige o maximize da janela: o tamanho inicial (1260x960) estourava a área
  útil de monitores menores (ex.: 1600x900, 1366x768), deixando o botão de
  maximizar inerte. Agora a janela inicial e o minsize são limitados à tela.
- Checagem de atualização aceita `zip_name` canônico e `-incremental`.
- `drive_upload.py` ganha o subcomando `rename` (a incremental sobe e assume
  o nome canônico `<version>.zip` no Drive, exigido por apps já publicados).

> Pacote full publicado no GitHub Releases (asset `20260813_002.zip`):
> sha256 `8e20242070a5dacc252bfbba547594cb6889f36cf8bc221eb8262bb9be9962ea`
> (digest conferido pelo próprio GitHub).
>
> Update incremental publicada no Google Drive (pasta 14NX28WcCAcRuCT7TM8HmSD2IF6yYUOc0):
> `20260813_002.zip` — 26.551.321 bytes,
> sha256 `52ac7a476dde496c0a37809efac5a0d5d69be3f869abdf1dbed053ae6f3a9747`,
> ID `1MgwOrh5-DupDBeUuL-y0a4DqEN-HM1AP`. O `latest.json` assinado (ID
> `14qU9b4wbyu7_6hAOvip6qhSG91E45BJ3`) aponta para a incremental.
