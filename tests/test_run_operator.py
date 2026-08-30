"""run-operator.sh must not steal an occupied port."""

import os
import socket
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class TestRunOperator(unittest.TestCase):
    def test_occupied_port_exits_without_binding(self):
        holder = socket.socket()
        holder.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        holder.bind(("0.0.0.0", 0))
        holder.listen(1)
        port = holder.getsockname()[1]
        env = os.environ.copy()
        env["HEXSTRIKE_PORT"] = str(port)
        try:
            result = subprocess.run(
                ["bash", str(ROOT / "deploy" / "run-operator.sh")],
                cwd=str(ROOT),
                env=env,
                capture_output=True,
                text=True,
                timeout=15,
            )
        finally:
            holder.close()
        self.assertEqual(result.returncode, 3)
        self.assertIn("already in use", result.stderr)
        self.assertNotIn("started pid", result.stdout)
