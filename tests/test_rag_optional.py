"""RAG must construct when optional chromadb/embeddings backends are absent."""

import tempfile
import unittest

from hexstrike_rag import HexStrikeRAG, get_rag


class TestRagOptionalBackends(unittest.TestCase):
    def test_constructs_without_chromadb(self):
        with tempfile.TemporaryDirectory() as tmp:
            rag = HexStrikeRAG(data_dir=tmp)
            self.assertIsNone(rag.client)
            self.assertIsNone(rag.embedder)
            self.assertEqual(
                rag.get_context_for_target("example.test"),
                {"findings": [], "summary": "RAG not available"},
            )

    def test_get_rag_singleton_does_not_raise(self):
        rag = get_rag()
        self.assertIsInstance(rag, HexStrikeRAG)
