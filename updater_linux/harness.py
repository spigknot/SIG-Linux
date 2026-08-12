"""Harness de integração do sig_updater.sh (SIG Linux).

Equivalente ao updater_v2/harness.py do Windows. Monta uma instalação
temporária simulada (sig de mentira, ffmpeg fake, vad_deps fake), executa o
updater bash real apontando para ela e verifica:

- zips inválidos/incompletos são rejeitados sem tocar a instalação;
- processo ativo bloqueia a transação;
- atualização válida é aplicada, validada e o app novo fica vivo;
- falha de inicialização aciona rollback e restaura a versão anterior.
"""

from __future__ import annotations

import hashlib
import shutil
import subprocess
import tempfile
import threading
import time
import uuid
import zipfile
from pathlib import Path


REQUIRED_ZIP_MEMBERS = ("sig", "_internal/base_library.zip", "sig_updater.sh")
# Marcadores de log exatamente como o _update_script_text() de src/sig_app.py gera.
SUCCESS_LOG_MARKER = "Atualizacao aplicada e validada."
ROLLBACK_LOG_MARKER = "Aplicando rollback."


def _hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _fake_sig_text(pidfile: Path) -> str:
    return (
        "#!/usr/bin/env bash\n"
        f'echo $$ > "{pidfile}"\n'
        "sleep 30\n"
    )


def _build_base(workspace: Path, pidfile: Path) -> Path:
    """Instalação simulada: sig fake + _internal + marcadores de runtime."""
    base = workspace / f"base-{uuid.uuid4().hex[:8]}"
    (base / "_internal").mkdir(parents=True)
    (base / "_internal" / "base_library.zip").write_bytes(b"dummy-internal")
    (base / "sig").write_text(_fake_sig_text(pidfile), encoding="utf-8")
    (base / "sig").chmod(0o755)
    (base / "sig_updater.sh").write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    (base / "ffmpeg").write_bytes(b"fake-ffmpeg")
    (base / "ffplay").write_bytes(b"fake-ffplay")
    (base / "vad_deps").mkdir()
    (base / "vad_deps" / "fixture.txt").write_text("fixture", encoding="utf-8")
    return base


def _zip_directory(source: Path, destination: Path, extras: dict[str, bytes] | None = None) -> None:
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=1) as archive:
        for path in sorted(source.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(source).as_posix())
        for name, data in (extras or {}).items():
            archive.writestr(name, data)


def _minimal_zip(destination: Path, missing: set[str] | None = None, extras: dict[str, bytes] | None = None) -> None:
    """Zip mínimo válido para os cenários de rejeição do updater bash."""
    missing = missing or set()
    with zipfile.ZipFile(destination, "w") as archive:
        for relative in REQUIRED_ZIP_MEMBERS:
            if any(relative == item or relative.startswith(item + "/") for item in missing):
                continue
            archive.writestr(relative, b"fixture")
        archive.writestr("vad_deps/fixture.txt", b"fixture")
        for name, data in (extras or {}).items():
            archive.writestr(name, data)


def _start_holder(seconds: int):
    holder = subprocess.Popen(
        ["sleep", str(seconds)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    # O updater espera o PID sumir da tabela de processos (kill -0). Sem um
    # wait()/poll(), o filho morto vira zombie e kill -0 continua retornando 0
    # até o pai reapar. Uma thread daemon reapa o holder assim que ele morre,
    # reproduzindo o comportamento real (o init reapa o SIG fechado).
    threading.Thread(target=holder.wait, daemon=True).start()
    return holder


def _run_updater(updater: Path, package: Path, target: Path, log: Path, pid: int, timeout: int) -> int:
    result = subprocess.run(
        [
            "/bin/bash",
            str(updater),
            "--zip",
            str(package),
            "--target",
            str(target),
            "--pid",
            str(pid),
            "--log",
            str(log),
        ],
        check=False,
        timeout=timeout,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return result.returncode


def _stop_sig(pidfile: Path) -> None:
    if not pidfile.is_file():
        return
    try:
        pid = int(pidfile.read_text(encoding="utf-8").strip())
        subprocess.run(["kill", "-9", str(pid)], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except (OSError, ValueError):
        pass
    try:
        pidfile.unlink()
    except OSError:
        pass


def _assert_rejected(updater: Path, package: Path, target: Path, workspace: Path, label: str) -> None:
    before = _hash(target / "sig") if (target / "sig").is_file() else None
    log = workspace / f"{label}.log"
    holder = _start_holder(1)
    try:
        code = _run_updater(updater, package, target, log, holder.pid, timeout=30)
    finally:
        if holder.poll() is None:
            holder.terminate()
            holder.wait(timeout=5)
    if code == 0:
        raise AssertionError(f"cenário {label} foi aceito inesperadamente")
    if before is not None and _hash(target / "sig") != before:
        raise AssertionError(f"cenário {label} alterou a instalação antes de falhar")


def run(updater: Path, package_zip: Path, timeout: int = 180) -> list[str]:
    if not updater.is_file():
        raise AssertionError(f"updater não encontrado: {updater}")
    if not package_zip.is_file():
        raise AssertionError(f"pacote base não encontrado: {package_zip}")

    # Preflight: o pacote que será publicado precisa ter os membros que o
    # próprio updater valida.
    with zipfile.ZipFile(package_zip) as archive:
        names = {entry.filename.replace("\\", "/") for entry in archive.infolist()}
        missing = [member for member in REQUIRED_ZIP_MEMBERS if member not in names]
    if missing:
        raise AssertionError(f"pacote base sem membros obrigatórios: {missing}")

    workspace = Path(tempfile.mkdtemp(prefix="sig-updater-harness-"))
    holders: list[subprocess.Popen] = []
    try:
        # ---------- cenários de rejeição (não podem tocar a instalação) ----------
        preflight_target = workspace / "preflight-target"
        shutil.copytree(_build_base(workspace, workspace / "preflight.pid"), preflight_target)

        bad_sig = workspace / "missing-sig.zip"
        _minimal_zip(bad_sig, {"sig"})
        _assert_rejected(updater, bad_sig, preflight_target, workspace, "missing-sig")

        bad_internal = workspace / "missing-internal.zip"
        _minimal_zip(bad_internal, {"_internal"})
        _assert_rejected(updater, bad_internal, preflight_target, workspace, "missing-internal")

        bad_updater = workspace / "missing-updater.zip"
        _minimal_zip(bad_updater, {"sig_updater.sh"})
        _assert_rejected(updater, bad_updater, preflight_target, workspace, "missing-updater")

        corrupt = workspace / "corrupt.zip"
        corrupt.write_bytes(b"not a zip")
        _assert_rejected(updater, corrupt, preflight_target, workspace, "corrupt-zip")

        # ---------- processo ativo bloqueia a transação ----------
        active_target = workspace / "active-target"
        shutil.copytree(_build_base(workspace, workspace / "active.pid"), active_target)
        active_holder = _start_holder(10)
        holders.append(active_holder)
        active_log = workspace / "active.log"
        before_sig = _hash(active_target / "sig")
        active_start = time.time()
        try:
            _run_updater(updater, package_zip, active_target, active_log, active_holder.pid, timeout=8)
            raise AssertionError("updater retornou com processo ativo; deveria estar bloqueado")
        except subprocess.TimeoutExpired:
            pass  # esperado: o updater aguarda o PID encerrar
        if time.time() - active_start < 4:
            raise AssertionError("o updater não aguardou o processo ativo")
        if _hash(active_target / "sig") != before_sig:
            raise AssertionError("processo ativo: instalação foi alterada")

        # ---------- caminho de sucesso (com resolução de destino) ----------
        success_pidfile = workspace / "success.pid"
        success_target = workspace / "success-target"
        shutil.copytree(_build_base(workspace, success_pidfile), success_target)
        # target aponta para um subdiretório sem marcadores; o updater precisa
        # subir até achar ffmpeg/vad_deps na raiz da instalação
        nested_target = success_target / "sub" / "dir"
        nested_target.mkdir(parents=True)
        marker = uuid.uuid4().hex
        success_zip_dir = workspace / "success-zip"
        success_zip_dir.mkdir()
        success_zip = success_zip_dir / "success.zip"
        _zip_directory(
            success_target,
            success_zip,
            {"_internal/release-test-marker.txt": marker.encode()},
        )
        success_log = workspace / "success.log"
        success_holder = _start_holder(2)
        holders.append(success_holder)
        code = _run_updater(updater, success_zip, nested_target, success_log, success_holder.pid, timeout=timeout)
        if code != 0:
            raise AssertionError(f"sucesso retornou {code}: {success_log.read_text(errors='replace')}")
        if (success_target / "_internal/release-test-marker.txt").read_text().strip() != marker:
            raise AssertionError("o pacote novo não foi instalado no cenário de sucesso")
        log_text = success_log.read_text(encoding="utf-8", errors="replace")
        if SUCCESS_LOG_MARKER not in log_text:
            raise AssertionError(f"o log de sucesso não contém a validação final:\n{log_text}")
        if "destino resolvido=" not in log_text:
            raise AssertionError("o log de sucesso não registra a resolução do destino")
        _stop_sig(success_pidfile)
        holders.remove(success_holder)
        if success_holder.poll() is None:
            success_holder.terminate()
            success_holder.wait(timeout=5)

        # ---------- rollback: sig novo que não inicia ----------
        rollback_pidfile = workspace / "rollback.pid"
        rollback_target = workspace / "rollback-target"
        shutil.copytree(_build_base(workspace, rollback_pidfile), rollback_target)
        old_hash = _hash(rollback_target / "sig")
        # pacote com o sig substituído por um script que sai imediatamente
        rollback_source = workspace / "rollback-source"
        shutil.copytree(rollback_target, rollback_source)
        (rollback_source / "sig").write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
        (rollback_source / "sig").chmod(0o755)
        bad_zip = workspace / "invalid-executable.zip"
        _zip_directory(rollback_source, bad_zip)
        rollback_log = workspace / "rollback.log"
        rollback_holder = _start_holder(2)
        holders.append(rollback_holder)
        rollback_code = _run_updater(updater, bad_zip, rollback_target, rollback_log, rollback_holder.pid, timeout=timeout)
        rollback_text = rollback_log.read_text(encoding="utf-8", errors="replace")
        _stop_sig(rollback_pidfile)
        holders.remove(rollback_holder)
        if rollback_holder.poll() is None:
            rollback_holder.terminate()
            rollback_holder.wait(timeout=5)
        if rollback_code == 0:
            raise AssertionError("pacote com sig que não inicia foi aceito")
        if _hash(rollback_target / "sig") != old_hash:
            raise AssertionError("rollback não restaurou o sig original")
        if ROLLBACK_LOG_MARKER not in rollback_text:
            raise AssertionError(f"o log não confirma rollback:\n{rollback_text}")

        return [
            "pacotes incompletos e zip corrompido foram rejeitados sem alterar a instalação",
            "processo ativo bloqueou a transação sem modificar a instalação",
            "atualização completa executou, resolveu o destino e validou o app novo",
            "falha de inicialização acionou rollback e restaurou a versão anterior",
        ]
    finally:
        for holder in holders:
            if holder.poll() is None:
                holder.terminate()
                holder.wait(timeout=5)
        shutil.rmtree(workspace, ignore_errors=True)


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--updater", type=Path, required=True)
    parser.add_argument("--package-zip", type=Path, required=True)
    parser.add_argument("--timeout", type=int, default=180)
    args = parser.parse_args()
    try:
        for message in run(args.updater.resolve(), args.package_zip.resolve(), args.timeout):
            print(f"PASS: {message}")
        return 0
    except Exception as exc:
        print(f"FAIL: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
