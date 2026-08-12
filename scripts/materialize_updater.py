#!/usr/bin/env python3
"""Materializa updater_linux/sig_updater.sh a partir de _update_script_text()."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from sig_app import SigApp  # noqa: E402

script = SigApp._update_script_text()
assert script.lstrip().startswith("#!/usr/bin/env bash"), "conteúdo inesperado"
out = Path(__file__).resolve().parents[1] / "updater_linux" / "sig_updater.sh"
out.write_text(script, encoding="utf-8")
out.chmod(0o755)
print(f"OK: {out} ({len(script)} bytes, {script.count(chr(10))} linhas)")
