"""Behavioral tests for HexForge v6.5 identity."""

import unittest

from hexstrike_identity import (
    ENHANCED_MODULE_NAMES,
    HEXFORGE_PRODUCT,
    HEXSTRIKE_EDITION,
    HEXSTRIKE_VERSION,
    health_identity,
    probe_enhanced_modules,
)


class TestHexStrikeIdentity(unittest.TestCase):
    def test_version_is_hexforge_v65(self):
        identity = health_identity()
        self.assertEqual(identity["product"], "HexForge")
        self.assertEqual(identity["version"], "6.5.0")
        self.assertEqual(identity["edition"], "hexforge")
        self.assertEqual(HEXFORGE_PRODUCT, "HexForge")
        self.assertEqual(HEXSTRIKE_VERSION, "6.5.0")
        self.assertEqual(HEXSTRIKE_EDITION, "hexforge")

    def test_all_enhanced_modules_import(self):
        modules = probe_enhanced_modules()
        expected = {name.removeprefix("hexstrike_") for name in ENHANCED_MODULE_NAMES}
        self.assertEqual(set(modules), expected)
        missing = [name for name, present in modules.items() if not present]
        self.assertEqual(missing, [], f"enhanced modules failed to import: {missing}")
        identity = health_identity()
        self.assertTrue(identity["v2_enabled"])
        self.assertTrue(all(identity["enhanced_modules"].values()))
        self.assertIn("chromadb", identity["rag_backends"])
        self.assertIn("embeddings", identity["rag_backends"])

    def test_module_probe_does_not_import_flask_server(self):
        import sys

        probe_enhanced_modules()
        self.assertNotIn(
            "hexstrike_server",
            sys.modules,
            "enhanced module probe must not load hexstrike_server.py",
        )


if __name__ == "__main__":
    unittest.main()
