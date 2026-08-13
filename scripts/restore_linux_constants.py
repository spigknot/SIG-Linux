"""Restaura as constantes próprias do SIG Linux (do backup) no novo sig_app.py."""
import re
from pathlib import Path

BACKUP = Path(r"/tmp/sig_linux_backup_13049.py")
SRC = Path(r"D:\Projetos\SIG Linux\src\sig_app.py")

backup = BACKUP.read_text(encoding="utf-8")
text = SRC.read_text(encoding="utf-8")

names = ("APP_VERSION", "UPDATE_MANIFEST_FILE_ID", "UPDATE_DOWNLOAD_URL",
         "UPDATE_PUBLIC_KEY_E", "UPDATE_PUBLIC_KEY_N")
for name in names:
    match = re.search(rf"^{name}\s*=\s*.*$", backup, re.MULTILINE)
    assert match, name
    old_line = re.search(rf"^{name}\s*=\s*.*$", text, re.MULTILINE)
    assert old_line, f"{name} não existe no novo arquivo"
    text = text.replace(old_line.group(0), match.group(0))

SRC.write_text(text, encoding="utf-8")
print("Constantes Linux restauradas:", *names, sep="\n  - ")
