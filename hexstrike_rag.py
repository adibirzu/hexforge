# File: hexstrike_rag.py
"""
RAG system for HexStrike.
ADDS semantic search - does not replace existing CVE system.
"""

import json
from typing import List, Dict, Optional, Any
from pathlib import Path
import os

# ChromaDB for local vector storage
try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    print("Warning: chromadb not installed. RAG features disabled.")

# Sentence transformers for embeddings
try:
    from sentence_transformers import SentenceTransformer
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False
    print("Warning: sentence-transformers not installed. Using basic search.")


class HexStrikeRAG:
    """
    RAG (Retrieval-Augmented Generation) system for HexStrike.
    Provides semantic search of past findings and knowledge.
    """

    def __init__(self, data_dir: str = None):
        if data_dir is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            data_dir = os.path.join(base_dir, "data", "rag")
            
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.client = None
        self.embedder = None
        self.findings_collection = None
        self.knowledge_collection = None

        self._init_chromadb()
        self._init_embeddings()

    def _init_chromadb(self):
        """Initialize ChromaDB"""
        if not CHROMADB_AVAILABLE:
            return

        try:
            # Persistent client
            self.client = chromadb.PersistentClient(path=str(self.data_dir / "chroma"))

            # Collection for vulnerability findings
            self.findings_collection = self.client.get_or_create_collection(
                name="findings",
                metadata={"description": "Vulnerability findings from scans"}
            )

            # Collection for general security knowledge
            self.knowledge_collection = self.client.get_or_create_collection(
                name="knowledge",
                metadata={"description": "Security knowledge base"}
            )
        except Exception as e:
            print(f"Error initializing ChromaDB: {e}")
            CHROMADB_AVAILABLE = False

    def _init_embeddings(self):
        """Initialize embedding model"""
        if not EMBEDDINGS_AVAILABLE:
            return

        try:
            # Use lightweight model for speed
            self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
        except Exception as e:
            print(f"Error initializing SentenceTransformer: {e}")
            EMBEDDINGS_AVAILABLE = False

    def _get_embedding(self, text: str) -> List[float]:
        """Get embedding for text"""
        if self.embedder:
            return self.embedder.encode(text).tolist()
        return []

    # ========== FINDINGS RAG ==========

    def index_finding(self, finding: Dict) -> str:
        """Index a finding for semantic search"""
        if not self.findings_collection:
            return ""

        # Create searchable text from finding
        text = self._finding_to_text(finding)
        embedding = self._get_embedding(text)

        finding_id = finding.get('id', str(hash(text)))

        self.findings_collection.add(
            ids=[finding_id],
            documents=[text],
            embeddings=[embedding] if embedding else None,
            metadatas=[{
                'project_id': finding.get('project_id', ''),
                'severity': finding.get('severity', ''),
                'finding_type': finding.get('finding_type', ''),
                'cve_id': finding.get('cve_id', ''),
                'location': finding.get('location', '')
            }]
        )

        return finding_id

    def _finding_to_text(self, finding: Dict) -> str:
        """Convert finding to searchable text"""
        parts = [
            f"Type: {finding.get('finding_type', 'unknown')}",
            f"Severity: {finding.get('severity', 'unknown')}",
            f"Title: {finding.get('title', '')}",
            f"Description: {finding.get('description', '')}",
            f"Location: {finding.get('location', '')}",
        ]
        if finding.get('cve_id'):
            parts.append(f"CVE: {finding['cve_id']}")
        if finding.get('evidence'):
            evidence = str(finding.get('evidence', ''))
            parts.append(f"Evidence: {evidence[:500]}")
        return "\n".join(parts)

    def search_similar_findings(self, query: str, n_results: int = 5,
                                 project_id: str = None) -> List[Dict]:
        """Find similar findings using semantic search"""
        if not self.findings_collection:
            return []

        where_filter = {"project_id": project_id} if project_id else None

        results = self.findings_collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where_filter
        )

        return self._format_search_results(results)

    def get_context_for_target(self, target: str, project_id: str = None) -> Dict:
        """Get relevant context for a target from past findings"""
        if not self.findings_collection:
            return {"findings": [], "summary": "RAG not available"}

        # Search for target-related findings
        results = self.search_similar_findings(
            query=f"target {target} vulnerability",
            n_results=10,
            project_id=project_id
        )

        # Summarize findings by severity
        summary = self._summarize_findings(results)

        return {
            "findings": results,
            "summary": summary,
            "target": target
        }

    def _summarize_findings(self, findings: List[Dict]) -> str:
        """Create summary of findings for context"""
        if not findings:
            return "No previous findings for this target."

        by_severity = {}
        for f in findings:
            metadata = f.get('metadata', {})
            if isinstance(metadata, dict):
                sev = metadata.get('severity', 'unknown')
            else:
                sev = 'unknown'
            by_severity.setdefault(sev, []).append(f)

        lines = ["Previous findings summary:"]
        for sev in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO', 'unknown']:
            if sev in by_severity:
                count = len(by_severity[sev])
                lines.append(f"  - {sev}: {count} finding(s)")

        return "\n".join(lines)

    # ========== KNOWLEDGE BASE ==========

    def add_knowledge(self, content: str, content_type: str,
                      source: str = None, metadata: dict = None) -> str:
        """Add knowledge to the knowledge base"""
        if not self.knowledge_collection:
            return ""

        knowledge_id = str(hash(content))
        embedding = self._get_embedding(content)

        self.knowledge_collection.add(
            ids=[knowledge_id],
            documents=[content],
            embeddings=[embedding] if embedding else None,
            metadatas=[{
                'content_type': content_type,
                'source': source or '',
                **(metadata or {})
            }]
        )

        return knowledge_id

    def query_knowledge(self, query: str, n_results: int = 5) -> List[Dict]:
        """Query knowledge base"""
        if not self.knowledge_collection:
            return []

        results = self.knowledge_collection.query(
            query_texts=[query],
            n_results=n_results
        )

        return self._format_search_results(results)

    def _format_search_results(self, results: Dict) -> List[Dict]:
        """Format ChromaDB results to consistent format"""
        formatted = []
        if results and results.get('documents'):
            for i, doc in enumerate(results['documents'][0]):
                formatted.append({
                    'id': results['ids'][0][i] if results.get('ids') else '',
                    'content': doc,
                    'metadata': results['metadatas'][0][i] if results.get('metadatas') else {},
                    'distance': results['distances'][0][i] if results.get('distances') else 0
                })
        return formatted

    # ========== CONTEXT ENRICHMENT ==========

    def enrich_request_context(self, request_type: str, target: str = None,
                                project_id: str = None) -> Dict:
        """
        Enrich a request with relevant context from RAG.
        This reduces token usage by providing focused context.
        """
        context = {
            "relevant_findings": [],
            "relevant_knowledge": [],
            "recommendations": []
        }

        # Get target-specific findings
        if target:
            target_context = self.get_context_for_target(target, project_id)
            context["relevant_findings"] = target_context.get("findings", [])[:3]
            context["target_summary"] = target_context.get("summary", "")

        # Get knowledge relevant to request type
        if request_type:
            knowledge = self.query_knowledge(request_type, n_results=3)
            context["relevant_knowledge"] = knowledge

        return context


# Singleton instance
_rag = None

def get_rag() -> HexStrikeRAG:
    """Get singleton RAG instance"""
    global _rag
    if _rag is None:
        _rag = HexStrikeRAG()
    return _rag
