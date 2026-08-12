"""Adapta release.py do Windows para o SIG Linux."""
from pathlib import Path

SRC = Path(r"D:\Projetos\SIG Linux\scripts\release.py")
text = SRC.read_text(encoding="utf-8")
changes = []

# 1) Docstring
old = '"""Official local build/release command for SIG Windows.'
new = '"""Official local build/release command for SIG Linux.'
assert old in text
text = text.replace(old, new)
changes.append("docstring")

# 2) check_build_environment: sem _sounddevice_data/PortAudio DLL bundlable
old = '''def check_build_environment() -> None:
    try:
        import PyInstaller  # noqa: F401
        import _sounddevice_data  # noqa: F401
        import sounddevice as sd
        import websocket
    except Exception as exc:
        raise ValidationError(
            f"ambiente de build inválido ({sys.executable}): {exc}. "
            "Use o Python configurado para o PyInstaller."
        ) from exc
    if not getattr(websocket, "WebSocketApp", None) or not getattr(websocket, "ABNF", None):
        raise ValidationError("websocket-client está instalado, mas sua API necessária não está disponível")
    portaudio = Path(str(getattr(sd, "_libname", "")))
    if not portaudio.is_file():
        raise ValidationError(f"PortAudio não está carregável no ambiente de build: {portaudio}")'''
new = '''def check_build_environment() -> None:
    try:
        import PyInstaller  # noqa: F401
        import sounddevice as sd
        import websocket
    except Exception as exc:
        raise ValidationError(
            f"ambiente de build inválido ({sys.executable}): {exc}. "
            "Use o Python configurado para o PyInstaller."
        ) from exc
    if not getattr(websocket, "WebSocketApp", None) or not getattr(websocket, "ABNF", None):
        raise ValidationError("websocket-client está instalado, mas sua API necessária não está disponível")
    portaudio = Path(str(getattr(sd, "_libname", "")))
    if not portaudio.is_file():
        raise ValidationError(
            f"PortAudio não está carregável no ambiente de build: {portaudio}; "
            "instale libportaudio2 (ex.: sudo apt install libportaudio2)"
        )'''
assert old in text
text = text.replace(old, new)
changes.append("check_build_environment")

# 3) copy_runtime_assets: ffmpeg/ffplay sem .exe, updater = sig_updater.sh
old = '''def copy_runtime_assets(runtime_root: Path, package_root: Path, updater_path: Path | None = None) -> None:
    required = ("ffmpeg.exe", "ffplay.exe", "vad_deps")
    for relative in required:
        source = runtime_root / relative
        if not source.exists():
            raise ValidationError(f"runtime asset ausente: {source}")
        destination = package_root / relative
        if source.is_dir():
            shutil.copytree(source, destination)
        else:
            shutil.copy2(source, destination)
    updater_source = updater_path or (runtime_root / "SigUpdater.exe")
    if not updater_source.is_file():
        raise ValidationError(f"SigUpdater.exe ausente: {updater_source}")
    shutil.copy2(updater_source, package_root / "SigUpdater.exe")'''
new = '''def copy_runtime_assets(runtime_root: Path, package_root: Path, updater_path: Path | None = None) -> None:
    required = ("ffmpeg", "ffplay", "vad_deps")
    for relative in required:
        source = runtime_root / relative
        if not source.exists():
            raise ValidationError(f"runtime asset ausente: {source}")
        destination = package_root / relative
        if source.is_dir():
            shutil.copytree(source, destination)
        else:
            shutil.copy2(source, destination)
    updater_source = updater_path or (runtime_root / "sig_updater.sh")
    if not updater_source.is_file():
        raise ValidationError(f"sig_updater.sh ausente: {updater_source}")
    shutil.copy2(updater_source, package_root / "sig_updater.sh")
    (package_root / "sig_updater.sh").chmod(0o755)'''
assert old in text
text = text.replace(old, new)
changes.append("copy_runtime_assets")

# 4) build_release: sem build do SigUpdater.exe (script versionado) + nome do exe
old = '''    check_build_environment()
    runtime_root = (args.runtime_root or root / "dist").resolve()
    runtime_manifest = root / "scripts/runtime_artifact.json"
    validate_runtime_assets(runtime_root, runtime_manifest)
    output_root = (args.output_root or root / "release/generated" / version).resolve()
    if output_root.exists() and any(output_root.iterdir()):
        raise ValidationError(f"diretório de saída não está vazio: {output_root}")
    output_root.mkdir(parents=True, exist_ok=True)
    build_started = time.time()
    build_id = uuid.uuid4().hex
    work_root = Path(tempfile.mkdtemp(prefix=f"sig-clean-build-{version}-"))
    try:
        updater_build_dir = work_root / "updater-dist"
        updater_work_dir = work_root / "updater-work"
        updater_environment = os.environ.copy()
        updater_environment["SOURCE_DATE_EPOCH"] = "946684800"
        updater_environment["PYTHONHASHSEED"] = "0"
        run_command(
            [
                sys.executable,
                "-m",
                "PyInstaller",
                "--noconfirm",
                "--clean",
                "--onefile",
                "--console",
                "--noupx",
                "--name",
                "SigUpdater",
                "--distpath",
                str(updater_build_dir),
                "--workpath",
                str(updater_work_dir),
                "--specpath",
                str(updater_work_dir),
                str(root / "updater_v2" / "updater.py"),
            ],
            root,
            output_root / "pyinstaller-updater.log",
            updater_environment,
        )
        fresh_updater = updater_build_dir / "SigUpdater.exe"
        if not fresh_updater.is_file():
            raise ValidationError("PyInstaller não produziu o SigUpdater.exe endurecido")
        pyinstaller_dist = work_root / "pyinstaller-dist"'''
new = '''    check_build_environment()
    runtime_root = (args.runtime_root or root / "dist").resolve()
    runtime_manifest = root / "scripts/runtime_artifact.json"
    validate_runtime_assets(runtime_root, runtime_manifest)
    output_root = (args.output_root or root / "release/generated" / version).resolve()
    if output_root.exists() and any(output_root.iterdir()):
        raise ValidationError(f"diretório de saída não está vazio: {output_root}")
    output_root.mkdir(parents=True, exist_ok=True)
    build_started = time.time()
    build_id = uuid.uuid4().hex
    work_root = Path(tempfile.mkdtemp(prefix=f"sig-clean-build-{version}-"))
    try:
        # O updater do Linux é um script bash versionado (updater_linux/sig_updater.sh),
        # não um executável compilado; validamos seu hash contra o artefato conhecido.
        fresh_updater = root / "updater_linux" / "sig_updater.sh"
        if not fresh_updater.is_file():
            raise ValidationError("updater_linux/sig_updater.sh ausente")
        updater_metadata = json.loads((root / "scripts/updater_artifact.json").read_text(encoding="utf-8"))
        if sha256_file(fresh_updater) != str(updater_metadata.get("sha256") or "").lower():
            raise ValidationError("sig_updater.sh não corresponde ao artifact.json")
        pyinstaller_dist = work_root / "pyinstaller-dist"'''
assert old in text
text = text.replace(old, new)
changes.append("build_release updater")

# 5) nome do exe validado: sig.exe -> sig
old = '        frozen_version = frozen_app_version(package_root / "sig.exe")'
new = '        frozen_version = frozen_app_version(package_root / "sig")'
assert old in text
text = text.replace(old, new)
changes.append("frozen sig")

old = '''                f"sig.exe recém-gerado contém {frozen_version}, esperado {version}"'''
new = '''                f"sig recém-gerado contém {frozen_version}, esperado {version}"'''
assert old in text
text = text.replace(old, new)
changes.append("msg frozen")

# 6) harness updater test: SigUpdater.exe -> sig_updater.sh
old = '''        from updater_v2.harness import run as run_updater_test

        for message in run_updater_test(
            package_root / "SigUpdater.exe",
            zip_path,
            args.updater_timeout,
        ):'''
new = '''        from updater_linux.harness import run as run_updater_test

        for message in run_updater_test(
            package_root / "sig_updater.sh",
            zip_path,
            args.updater_timeout,
        ):'''
assert old in text
text = text.replace(old, new)
changes.append("harness")

SRC.write_text(text, encoding="utf-8")
print("Aplicadas:", *changes, sep="\n  - ")
