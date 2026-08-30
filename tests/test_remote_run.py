"""remote-run.sh fails closed when the documented KaliVM key is missing."""

import os
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class TestRemoteRun(unittest.TestCase):
    def test_missing_key_exits_nonzero_without_ssh(self):
        env = os.environ.copy()
        env["KALI_SSH_KEY"] = str(ROOT / "no-such-kali-key")
        result = subprocess.run(
            ["bash", str(ROOT / "deploy" / "remote-run.sh"), "inventory"],
            cwd=str(ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(result.returncode, 3)
        self.assertIn("missing SSH key", result.stderr)
        self.assertIn("no-such-kali-key", result.stderr)
