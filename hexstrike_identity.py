"""Canonical HexForge identity for health and clients.

Kept free of Flask/tool imports so tests can probe edition and modules
without loading hexstrike_server.py.
"""

from __future__ import annotations

import importlib
from typing import Any, Dict, Optional

HEXFORGE_PRODUCT = "HexForge"
HEXSTRIKE_VERSION = "6.5.0"
HEXSTRIKE_EDITION = "hexforge"

ENHANCED_MODULE_NAMES = (
    "hexstrike_persistence",
    "hexstrike_rag",
    "hexstrike_checkpoint",
    "hexstrike_optimizer",
    "hexstrike_evolution",
    "hexstrike_reporting",
)


def probe_enhanced_modules() -> Dict[str, bool]:
    """Return importability of each v6.5 module (short name -> bool)."""
    status: Dict[str, bool] = {}
    for name in ENHANCED_MODULE_NAMES:
        short = name.removeprefix("hexstrike_")
        try:
            importlib.import_module(name)
            status[short] = True
        except Exception:
            status[short] = False
    return status


def probe_rag_backends() -> Dict[str, bool]:
    """Report optional RAG backends without requiring them at install time."""
    try:
        rag = importlib.import_module("hexstrike_rag")
        return {
            "chromadb": bool(getattr(rag, "CHROMADB_AVAILABLE", False)),
            "embeddings": bool(getattr(rag, "EMBEDDINGS_AVAILABLE", False)),
        }
    except Exception:
        return {"chromadb": False, "embeddings": False}


def health_identity(v2_enabled: Optional[bool] = None) -> Dict[str, Any]:
    """Fields that distinguish HexForge v6.5 from upstream HexStrike v6.0."""
    modules = probe_enhanced_modules()
    if v2_enabled is None:
        v2_enabled = all(modules.values())
    return {
        "product": HEXFORGE_PRODUCT,
        "version": HEXSTRIKE_VERSION,
        "edition": HEXSTRIKE_EDITION,
        "v2_enabled": bool(v2_enabled),
        "enhanced_modules": modules,
        "rag_backends": probe_rag_backends(),
    }
