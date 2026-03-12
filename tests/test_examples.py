import os
import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_DIRS = [
    "01-traffic-light",
    "02-todo-workflow",
    "03-retrying-job",
]


class ExampleSnapshotTests(unittest.TestCase):
    def test_examples_match_committed_specs(self) -> None:
        env = os.environ.copy()
        env["PYTHONPATH"] = str(REPO_ROOT)

        for directory in EXAMPLE_DIRS:
            with self.subTest(example=directory):
                build_script = REPO_ROOT / "examples" / directory / "build.py"
                spec_path = REPO_ROOT / "examples" / directory / "spec.tla"

                result = subprocess.run(
                    [sys.executable, str(build_script)],
                    check=True,
                    capture_output=True,
                    cwd=REPO_ROOT,
                    env=env,
                    text=True,
                )

                self.assertEqual(result.stdout.rstrip() + "\n", spec_path.read_text(encoding="utf-8"))
