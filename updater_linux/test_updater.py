"""Regressão do harness do updater Linux com um pacote mínimo de teste."""

from __future__ import annotations

import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "updater_linux"))


def _make_minimal_test_zip(destination: Path) -> None:
    with zipfile.ZipFile(destination, "w") as archive:
        archive.writestr("sig", "#!/usr/bin/env bash\nexit 0\n")
        archive.writestr("_internal/base_library.zip", b"dummy")
        archive.writestr("_internal/libpython3.11.so.1.0", b"dummy")
        archive.writestr("sig_updater.sh", "#!/usr/bin/env bash\nexit 0\n")
        archive.writestr("sig_updater.py", "print('fixture')\n")
        archive.writestr("ffmpeg", b"fixture")
        archive.writestr("ffplay", b"fixture")
        archive.writestr("vad_worker.py", b"print('fixture')\n")
        archive.writestr("vad_deps/fixture.txt", b"fixture")


class UpdaterHarnessTests(unittest.TestCase):
    def test_full_harness_with_minimal_package(self) -> None:
        from harness import run

        updater = ROOT / "updater_linux" / "sig_updater.sh"
        self.assertTrue(updater.is_file(), "sig_updater.sh não materializado")
        with tempfile.TemporaryDirectory() as temporary:
            package_zip = Path(temporary) / "test-package.zip"
            _make_minimal_test_zip(package_zip)
            messages = run(updater, package_zip, timeout=120)
        self.assertEqual(len(messages), 4, messages)


if __name__ == "__main__":
    unittest.main()
