import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _venv_python(venv_dir: Path) -> Path:
    if os.name == "nt":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


class PackageSmokeTests(unittest.TestCase):
    def test_editable_install_imports_and_cli_help(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            venv_dir = Path(tmp_dir) / "venv"
            env = os.environ.copy()
            env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"

            subprocess.run(
                [sys.executable, "-m", "venv", str(venv_dir)],
                check=True,
                cwd=REPO_ROOT,
                env=env,
            )

            python_bin = _venv_python(venv_dir)

            subprocess.run(
                [
                    str(python_bin),
                    "-m",
                    "pip",
                    "install",
                    "--no-build-isolation",
                    "-e",
                    str(REPO_ROOT),
                ],
                check=True,
                capture_output=True,
                cwd=REPO_ROOT,
                env=env,
                text=True,
            )

            import_result = subprocess.run(
                [
                    str(python_bin),
                    "-c",
                    (
                        "from tlaforge import Definition, StateMachineSpec, "
                        "StateTransition, TLAForgeAgent; "
                        "print(StateMachineSpec.__name__); "
                        "print(TLAForgeAgent.__name__)"
                    ),
                ],
                check=True,
                capture_output=True,
                cwd=REPO_ROOT,
                env=env,
                text=True,
            )
            self.assertEqual(
                import_result.stdout.strip().splitlines(),
                ["StateMachineSpec", "TLAForgeAgent"],
            )

            help_result = subprocess.run(
                [str(python_bin), "-m", "tlaforge.cli", "--help"],
                check=True,
                capture_output=True,
                cwd=REPO_ROOT,
                env=env,
                text=True,
            )
            self.assertIn("usage:", help_result.stdout)
            self.assertIn("--traffic", help_result.stdout)
