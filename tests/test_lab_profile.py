import asyncio
import importlib
import os
import sys
import types
import unittest
from unittest.mock import patch

from hexstrike_lab import DEFAULT_API_HOST, is_lab_blocked_path


class StubClient:
    def safe_get(self, *args, **kwargs):
        return {}

    def safe_post(self, *args, **kwargs):
        return {}

    def execute_command(self, *args, **kwargs):
        return {}


class StubFastMCP:
    def __init__(self, name):
        self.name = name
        self._tools = []

    def tool(self):
        def register(function):
            self._tools.append(types.SimpleNamespace(name=function.__name__))
            return function

        return register

    async def list_tools(self):
        return self._tools


class LabProfileMcpTests(unittest.TestCase):
    def tool_names(self, enabled):
        environment = {"AETHEROPS_LAB": "1"} if enabled else {}
        fastmcp = types.ModuleType("mcp.server.fastmcp")
        fastmcp.FastMCP = StubFastMCP
        with (
            patch.dict(os.environ, environment, clear=True),
            patch.dict(sys.modules, {"mcp.server.fastmcp": fastmcp}),
        ):
            import hexstrike_mcp

            module = importlib.reload(hexstrike_mcp)
            server = module.setup_mcp_server(StubClient())
            tools = asyncio.run(server.list_tools())
        return [tool.name for tool in tools]

    def test_lab_profile_hides_dangerous_tools_and_deduplicates_httpx(self):
        names = self.tool_names(enabled=True)

        self.assertNotIn("execute_command", names)
        self.assertNotIn("generate_payload", names)
        self.assertEqual(names.count("httpx_probe"), 1)

    def test_default_profile_keeps_dangerous_tools(self):
        names = self.tool_names(enabled=False)

        self.assertIn("execute_command", names)
        self.assertIn("generate_payload", names)
        self.assertEqual(names.count("httpx_probe"), 1)


class LabProfileApiTests(unittest.TestCase):
    def test_server_defaults_to_loopback(self):
        self.assertEqual(DEFAULT_API_HOST, "127.0.0.1")

    def test_lab_profile_blocks_only_execution_endpoints(self):
        with patch.dict(os.environ, {"AETHEROPS_LAB": "1"}, clear=True):
            self.assertTrue(is_lab_blocked_path("/api/command"))
            self.assertTrue(is_lab_blocked_path("/api/payloads/generate"))
            self.assertTrue(is_lab_blocked_path("/api/v2/evolution/execute"))
            self.assertFalse(is_lab_blocked_path("/health"))
            self.assertFalse(is_lab_blocked_path("/api/v2/evolution/learned"))

    def test_default_profile_does_not_block_execution_endpoints(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(is_lab_blocked_path("/api/command"))
