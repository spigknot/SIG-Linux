"""Reaplica as adaptações Linux básicas no sig_app.py (copiado do Windows)."""
from pathlib import Path

SRC = Path(r"D:\Projetos\SIG Linux\src\sig_app.py")
text = SRC.read_text(encoding="utf-8")
changes = []


def rep(old, new, label, count=1):
    global text
    found = text.count(old)
    assert found >= count, f"{label}: padrão não encontrado ({found})"
    text = text.replace(old, new, count)
    changes.append(label)


# 1) runtime_markers sem extensão
rep('runtime_markers = ("ffmpeg.exe", "ffplay.exe", "vad_deps")',
    'runtime_markers = ("ffmpeg", "ffplay", "vad_deps", "ffmpeg.exe", "ffplay.exe")',
    "runtime_markers")

# 2) settings_path XDG
rep('''def settings_path() -> Path:
    base = Path(os.environ.get("APPDATA", str(Path.home()))) / APP_NAME''',
    '''def settings_path() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", str(Path.home()))) / APP_NAME
    else:
        config_home = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
        base = Path(config_home) / APP_NAME''',
    "settings_path")

# 3) _ffplay
rep('''    def _ffplay(self) -> Path:
        path = app_base_dir() / "ffplay.exe"
        if not path.exists():
            raise RuntimeError("ffplay.exe não foi encontrado na pasta do aplicativo")
        return path''',
    '''    def _ffplay(self) -> Path:
        if os.name == "nt":
            path = app_base_dir() / "ffplay.exe"
            if not path.exists():
                raise RuntimeError("ffplay.exe não foi encontrado na pasta do aplicativo")
            return path
        local = app_base_dir() / "ffplay"
        if local.exists():
            return local
        from shutil import which
        found = which("ffplay")
        if found:
            return Path(found)
        raise RuntimeError("ffplay não foi encontrado na pasta do aplicativo nem no PATH")''',
    "_ffplay")

# 4) _ffmpeg
rep('''    def _ffmpeg(self) -> Path:
        path = app_base_dir() / "ffmpeg.exe"
        if not path.exists():
            raise RuntimeError("ffmpeg.exe não foi encontrado na pasta do aplicativo")
        return path''',
    '''    def _ffmpeg(self) -> Path:
        if os.name == "nt":
            path = app_base_dir() / "ffmpeg.exe"
            if not path.exists():
                raise RuntimeError("ffmpeg.exe não foi encontrado na pasta do aplicativo")
            return path
        local = app_base_dir() / "ffmpeg"
        if local.exists():
            return local
        from shutil import which
        found = which("ffmpeg")
        if found:
            return Path(found)
        raise RuntimeError("ffmpeg não foi encontrado na pasta do aplicativo nem no PATH")''',
    "_ffmpeg")

# 5) _get_ffprobe
rep('''            candidate = ffmpeg.parent / "ffprobe.exe"
            if candidate.exists():
                return candidate''',
    '''            candidate = ffmpeg.parent / ("ffprobe.exe" if os.name == "nt" else "ffprobe")
            if candidate.exists():
                return candidate
            if os.name != "nt":
                from shutil import which
                found = which("ffprobe")
                if found:
                    return Path(found)''',
    "_get_ffprobe")

# 6) open_output_dir
rep('''            if os.name == "nt":
                os.startfile(self.output_dir)
            else:
                webbrowser.open(self.output_dir.as_uri())''',
    '''            if os.name == "nt":
                os.startfile(self.output_dir)
            else:
                subprocess.Popen(
                    ["xdg-open", str(self.output_dir)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )''',
    "open_output_dir")

# 7) os.startfile(temp_dir) — substitui TODAS as ocorrências restantes
old = "os.startfile(temp_dir)"
new = '''os.startfile(temp_dir) if os.name == "nt" else subprocess.Popen(
                    ["xdg-open", str(temp_dir)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )'''
count = text.count(old)
assert count >= 1, "os.startfile(temp_dir) não encontrado"
text = text.replace(old, new)
changes.append(f"os.startfile(temp_dir) x{count}")

# 8) os.startfile(path) genérico restante
old = "os.startfile(path)"
if old in text:
    text = text.replace(old, '''os.startfile(path) if os.name == "nt" else subprocess.Popen(
                    ["xdg-open", str(path)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )''')
    changes.append("os.startfile(path)")

# 9) conversion: ffmpeg fixo → self._ffmpeg()
rep('''        ffmpeg = app_base_dir() / "ffmpeg.exe"
        if not ffmpeg.exists():
            raise RuntimeError(f"ffmpeg.exe não encontrado: {ffmpeg}")''',
    '''        ffmpeg = self._ffmpeg()
        if not ffmpeg.exists():
            raise RuntimeError(f"ffmpeg não encontrado: {ffmpeg}")''',
    "conversion _ffmpeg")

SRC.write_text(text, encoding="utf-8")
print("Aplicadas:", *changes, sep="\n  - ")
