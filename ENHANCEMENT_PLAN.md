# HexForge Enhancement Plan v2.1

## Focused Improvements - Only Missing Features

**Created:** 2025-12-05
**Updated:** 2025-12-05 (Compared with existing codebase)
**Status:** Planning Phase
**Goal:** Add persistence, checkpoints, RAG, and token optimization WITHOUT breaking existing features

---

## Existing Features Analysis

### What HexStrike ALREADY HAS (Do Not Duplicate):

| Category | Existing Implementation | Location |
|----------|------------------------|----------|
| **In-Memory Cache** | AdvancedCache (LRU, TTL, thread-safe) | `hexstrike_server.py:5085` |
| **Secondary Cache** | HexStrikeCache (1000 entries, 1hr TTL) | `hexstrike_server.py:6668` |
| **Error Recovery** | IntelligentErrorHandler (11 error types, retry logic) | `hexstrike_server.py:1606` |
| **Failure Recovery** | FailureRecoverySystem (tool alternatives) | `hexstrike_server.py:4449` |
| **Graceful Degradation** | GracefulDegradation (fallback chains) | `hexstrike_server.py:2201` |
| **Rate Limiting** | RateLimitDetector (adaptive timing) | `hexstrike_server.py:4344` |
| **Process Management** | EnhancedProcessManager (pause/resume) | `hexstrike_server.py:5208` |
| **CVE Knowledge** | CVEIntelligenceManager (NVD API) | `hexstrike_server.py:5750` |
| **Exploit Templates** | AIExploitGenerator (8 exploit types) | `hexstrike_server.py:7027` |
| **Vulnerability Correlation** | VulnerabilityCorrelator | `hexstrike_server.py:8510` |
| **Tech Detection** | TechnologyDetector (500+ signatures) | `hexstrike_server.py:4223` |
| **Bug Bounty Workflows** | BugBountyWorkflowManager (4 phases) | `hexstrike_server.py:2447` |
| **CTF Workflows** | CTFWorkflowManager (7 categories) | `hexstrike_server.py:2795` |
| **Attack Chains** | AttackChain class (step sequencing) | `hexstrike_server.py:522` |
| **Decision Engine** | IntelligentDecisionEngine | `hexstrike_server.py:572` |
| **CTF Automation** | CTFChallengeAutomator | `hexstrike_server.py:3855` |
| **Team Coordination** | CTFTeamCoordinator | `hexstrike_server.py:4072` |
| **Target Profiling** | TargetProfile dataclass | `hexstrike_server.py:474` |

### What's TRULY MISSING:

1. **Persistent Storage** - All data lost on restart
2. **Checkpoint System** - Cannot resume interrupted scans
3. **Project/Session Management** - No way to organize work
4. **Vector Database for RAG** - No semantic search of findings
5. **Token Optimization** - No compression/summarization
6. **Incremental Updates** - Full context sent every time

---

## Table of Contents

1. [Architecture Integration Strategy](#1-architecture-integration-strategy)
2. [Phase 1: Persistence Layer](#2-phase-1-persistence-layer)
3. [Phase 2: Checkpoint System](#3-phase-2-checkpoint-system)
4. [Phase 3: RAG Integration](#4-phase-3-rag-integration)
5. [Phase 4: Token Optimization](#5-phase-4-token-optimization)
6. [Implementation Safety](#6-implementation-safety)
7. [API Additions](#7-api-additions)
8. [File Changes](#8-file-changes)

---

## 1. Architecture Integration Strategy

### Design Principle: Wrapper Pattern

All new features will **wrap** existing functionality, not replace it.

```
┌─────────────────────────────────────────────────────────────────┐
│                    NEW: Persistence Layer                       │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────┐        │
│  │ ProjectMgr   │  │ SessionMgr   │  │ CheckpointMgr  │        │
│  └──────┬───────┘  └──────┬───────┘  └───────┬────────┘        │
└─────────┼─────────────────┼──────────────────┼──────────────────┘
          │                 │                  │
          ▼                 ▼                  ▼
┌─────────────────────────────────────────────────────────────────┐
│              EXISTING: hexstrike_server.py (UNCHANGED)          │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────┐        │
│  │AdvancedCache │  │ ErrorHandler │  │ DecisionEngine │        │
│  │ (in-memory)  │  │ (recovery)   │  │ (tool select)  │        │
│  └──────────────┘  └──────────────┘  └────────────────┘        │
└─────────────────────────────────────────────────────────────────┘
```

### Integration Points (Non-Breaking):

1. **New file**: `hexstrike_persistence.py` - imports and wraps existing classes
2. **New file**: `hexstrike_rag.py` - adds vector search alongside existing CVE system
3. **New file**: `hexstrike_optimizer.py` - post-processes responses
4. **Modified**: `hexstrike_server.py` - add new endpoints (existing untouched)
5. **Modified**: `hexstrike_mcp.py` - add new MCP tools (existing untouched)

---

## 2. Phase 1: Persistence Layer

### 2.1 What We're Adding (Not Replacing)

| New Feature | Complements Existing |
|-------------|---------------------|
| SQLite database | Works alongside AdvancedCache |
| Project storage | Extends TargetProfile persistence |
| Session tracking | Adds history to existing workflows |
| Finding storage | Persists VulnerabilityCorrelator results |

### 2.2 Database Schema

```sql
-- File: schemas/hexstrike_db.sql
-- NOTE: This ADDS persistence, does not replace in-memory cache

-- Projects (new concept)
CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    target TEXT NOT NULL,
    target_type TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'active',
    -- Store existing TargetProfile as JSON
    target_profile JSON,
    metadata JSON
);

-- Sessions (tracks work sessions)
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP,
    status TEXT DEFAULT 'active',
    -- Links to existing AttackChain if any
    attack_chain JSON,
    context JSON,
    FOREIGN KEY (project_id) REFERENCES projects(id)
);

-- Scans (persists tool executions)
CREATE TABLE IF NOT EXISTS scans (
    id TEXT PRIMARY KEY,
    session_id TEXT,
    project_id TEXT NOT NULL,
    tool TEXT NOT NULL,
    command TEXT,
    parameters JSON,
    status TEXT DEFAULT 'pending',
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    -- Store raw output for later retrieval
    stdout TEXT,
    stderr TEXT,
    return_code INTEGER,
    execution_time REAL,
    -- Checkpoint data for resume capability
    checkpoint_data JSON,
    progress INTEGER DEFAULT 0,
    -- Recovery info from existing IntelligentErrorHandler
    recovery_info JSON,
    FOREIGN KEY (session_id) REFERENCES sessions(id),
    FOREIGN KEY (project_id) REFERENCES projects(id)
);

-- Findings (persists discovered vulnerabilities)
CREATE TABLE IF NOT EXISTS findings (
    id TEXT PRIMARY KEY,
    scan_id TEXT,
    project_id TEXT NOT NULL,
    finding_type TEXT NOT NULL,
    severity TEXT,
    title TEXT NOT NULL,
    description TEXT,
    evidence TEXT,
    location TEXT,
    cve_id TEXT,
    cvss_score REAL,
    -- For RAG embedding reference
    embedding_id TEXT,
    raw_data JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (scan_id) REFERENCES scans(id),
    FOREIGN KEY (project_id) REFERENCES projects(id)
);

-- Checkpoints (for resume capability)
CREATE TABLE IF NOT EXISTS checkpoints (
    id TEXT PRIMARY KEY,
    scan_id TEXT NOT NULL,
    checkpoint_num INTEGER NOT NULL,
    state JSON NOT NULL,
    output_snapshot TEXT,
    progress INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (scan_id) REFERENCES scans(id)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_scans_project ON scans(project_id);
CREATE INDEX IF NOT EXISTS idx_scans_status ON scans(status);
CREATE INDEX IF NOT EXISTS idx_findings_project ON findings(project_id);
CREATE INDEX IF NOT EXISTS idx_findings_severity ON findings(severity);
CREATE INDEX IF NOT EXISTS idx_checkpoints_scan ON checkpoints(scan_id);
```

### 2.3 Persistence Manager Implementation

```python
# File: hexstrike_persistence.py
"""
HexStrike Persistence Layer
Adds persistent storage WITHOUT modifying existing classes
"""

import sqlite3
import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path
import threading

# Import existing classes to serialize their output
# These imports are READ-ONLY - we don't modify these classes
try:
    from hexstrike_server import TargetProfile, AttackChain
except ImportError:
    TargetProfile = None
    AttackChain = None


class HexStrikePersistence:
    """
    Persistence layer that WRAPS existing functionality.
    Does not replace AdvancedCache or any existing caching.
    """

    def __init__(self, db_path: str = "data/hexstrike.db"):
        self.db_path = db_path
        self._ensure_data_dir()
        self._init_db()
        self._local = threading.local()

    def _ensure_data_dir(self):
        """Create data directory if it doesn't exist"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

    def _get_conn(self):
        """Get thread-local database connection"""
        if not hasattr(self._local, 'conn'):
            self._local.conn = sqlite3.connect(self.db_path)
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn

    def _init_db(self):
        """Initialize database schema"""
        schema_path = Path(__file__).parent / "schemas" / "hexstrike_db.sql"
        if schema_path.exists():
            with open(schema_path) as f:
                self._get_conn().executescript(f.read())
        self._get_conn().commit()

    # ========== PROJECT MANAGEMENT ==========

    def create_project(self, name: str, target: str, description: str = "",
                       target_type: str = None, metadata: dict = None) -> str:
        """Create a new project"""
        project_id = str(uuid.uuid4())
        conn = self._get_conn()
        conn.execute("""
            INSERT INTO projects (id, name, target, description, target_type, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (project_id, name, target, description, target_type,
              json.dumps(metadata or {})))
        conn.commit()
        return project_id

    def get_project(self, project_id: str) -> Optional[Dict]:
        """Get project by ID"""
        cursor = self._get_conn().execute(
            "SELECT * FROM projects WHERE id = ?", (project_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def list_projects(self, status: str = None) -> List[Dict]:
        """List all projects, optionally filtered by status"""
        query = "SELECT * FROM projects"
        params = []
        if status:
            query += " WHERE status = ?"
            params.append(status)
        query += " ORDER BY updated_at DESC"
        cursor = self._get_conn().execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    def update_project(self, project_id: str, **kwargs) -> bool:
        """Update project fields"""
        allowed = ['name', 'description', 'target_type', 'status',
                   'target_profile', 'metadata']
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return False

        # Serialize JSON fields
        for field in ['target_profile', 'metadata']:
            if field in updates and isinstance(updates[field], dict):
                updates[field] = json.dumps(updates[field])

        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [project_id]

        conn = self._get_conn()
        conn.execute(f"""
            UPDATE projects SET {set_clause}, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, values)
        conn.commit()
        return True

    def save_target_profile(self, project_id: str, profile: 'TargetProfile'):
        """
        Save existing TargetProfile to persistent storage.
        This EXTENDS the existing class, doesn't replace it.
        """
        if hasattr(profile, 'to_dict'):
            profile_dict = profile.to_dict()
        else:
            profile_dict = vars(profile) if hasattr(profile, '__dict__') else {}

        self.update_project(project_id, target_profile=profile_dict)

    # ========== SESSION MANAGEMENT ==========

    def start_session(self, project_id: str, context: dict = None) -> str:
        """Start a new session for a project"""
        session_id = str(uuid.uuid4())
        conn = self._get_conn()
        conn.execute("""
            INSERT INTO sessions (id, project_id, context)
            VALUES (?, ?, ?)
        """, (session_id, project_id, json.dumps(context or {})))
        conn.commit()
        return session_id

    def end_session(self, session_id: str):
        """End a session"""
        conn = self._get_conn()
        conn.execute("""
            UPDATE sessions SET ended_at = CURRENT_TIMESTAMP, status = 'completed'
            WHERE id = ?
        """, (session_id,))
        conn.commit()

    def get_session(self, session_id: str) -> Optional[Dict]:
        """Get session by ID"""
        cursor = self._get_conn().execute(
            "SELECT * FROM sessions WHERE id = ?", (session_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_project_sessions(self, project_id: str) -> List[Dict]:
        """Get all sessions for a project"""
        cursor = self._get_conn().execute("""
            SELECT * FROM sessions WHERE project_id = ?
            ORDER BY started_at DESC
        """, (project_id,))
        return [dict(row) for row in cursor.fetchall()]

    # ========== SCAN PERSISTENCE ==========

    def start_scan(self, project_id: str, tool: str, command: str,
                   parameters: dict = None, session_id: str = None) -> str:
        """Record start of a scan"""
        scan_id = str(uuid.uuid4())
        conn = self._get_conn()
        conn.execute("""
            INSERT INTO scans (id, project_id, session_id, tool, command,
                              parameters, status, started_at)
            VALUES (?, ?, ?, ?, ?, ?, 'running', CURRENT_TIMESTAMP)
        """, (scan_id, project_id, session_id, tool, command,
              json.dumps(parameters or {})))
        conn.commit()
        return scan_id

    def update_scan_progress(self, scan_id: str, progress: int,
                             checkpoint_data: dict = None):
        """Update scan progress (called periodically)"""
        conn = self._get_conn()
        conn.execute("""
            UPDATE scans SET progress = ?, checkpoint_data = ?
            WHERE id = ?
        """, (progress, json.dumps(checkpoint_data or {}), scan_id))
        conn.commit()

    def complete_scan(self, scan_id: str, stdout: str, stderr: str,
                      return_code: int, execution_time: float,
                      recovery_info: dict = None):
        """Record scan completion with results"""
        conn = self._get_conn()
        status = 'completed' if return_code == 0 else 'failed'
        conn.execute("""
            UPDATE scans SET status = ?, stdout = ?, stderr = ?,
                   return_code = ?, execution_time = ?, recovery_info = ?,
                   completed_at = CURRENT_TIMESTAMP, progress = 100
            WHERE id = ?
        """, (status, stdout, stderr, return_code, execution_time,
              json.dumps(recovery_info or {}), scan_id))
        conn.commit()

    def get_scan(self, scan_id: str) -> Optional[Dict]:
        """Get scan by ID"""
        cursor = self._get_conn().execute(
            "SELECT * FROM scans WHERE id = ?", (scan_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_incomplete_scans(self, project_id: str = None) -> List[Dict]:
        """Get scans that can be resumed"""
        query = "SELECT * FROM scans WHERE status = 'running'"
        params = []
        if project_id:
            query += " AND project_id = ?"
            params.append(project_id)
        cursor = self._get_conn().execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    # ========== CHECKPOINT SYSTEM ==========

    def save_checkpoint(self, scan_id: str, state: dict,
                        output_snapshot: str, progress: int) -> str:
        """Save a checkpoint for resumable scans"""
        checkpoint_id = str(uuid.uuid4())
        conn = self._get_conn()

        # Get next checkpoint number
        cursor = conn.execute(
            "SELECT MAX(checkpoint_num) FROM checkpoints WHERE scan_id = ?",
            (scan_id,))
        max_num = cursor.fetchone()[0] or 0

        conn.execute("""
            INSERT INTO checkpoints (id, scan_id, checkpoint_num, state,
                                    output_snapshot, progress)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (checkpoint_id, scan_id, max_num + 1, json.dumps(state),
              output_snapshot, progress))
        conn.commit()
        return checkpoint_id

    def get_latest_checkpoint(self, scan_id: str) -> Optional[Dict]:
        """Get the latest checkpoint for a scan"""
        cursor = self._get_conn().execute("""
            SELECT * FROM checkpoints WHERE scan_id = ?
            ORDER BY checkpoint_num DESC LIMIT 1
        """, (scan_id,))
        row = cursor.fetchone()
        if row:
            result = dict(row)
            result['state'] = json.loads(result['state'])
            return result
        return None

    # ========== FINDINGS STORAGE ==========

    def save_finding(self, project_id: str, finding_type: str, title: str,
                     severity: str = None, description: str = None,
                     evidence: str = None, location: str = None,
                     cve_id: str = None, cvss_score: float = None,
                     scan_id: str = None, raw_data: dict = None) -> str:
        """Save a vulnerability finding"""
        finding_id = str(uuid.uuid4())
        conn = self._get_conn()
        conn.execute("""
            INSERT INTO findings (id, project_id, scan_id, finding_type, title,
                                 severity, description, evidence, location,
                                 cve_id, cvss_score, raw_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (finding_id, project_id, scan_id, finding_type, title,
              severity, description, evidence, location, cve_id, cvss_score,
              json.dumps(raw_data or {})))
        conn.commit()
        return finding_id

    def get_project_findings(self, project_id: str,
                             severity: str = None) -> List[Dict]:
        """Get all findings for a project"""
        query = "SELECT * FROM findings WHERE project_id = ?"
        params = [project_id]
        if severity:
            query += " AND severity = ?"
            params.append(severity)
        query += " ORDER BY created_at DESC"
        cursor = self._get_conn().execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    def search_findings(self, query: str, project_id: str = None) -> List[Dict]:
        """Search findings by text"""
        sql = """
            SELECT * FROM findings
            WHERE (title LIKE ? OR description LIKE ? OR location LIKE ?)
        """
        params = [f"%{query}%", f"%{query}%", f"%{query}%"]
        if project_id:
            sql += " AND project_id = ?"
            params.append(project_id)
        sql += " ORDER BY severity DESC, created_at DESC"
        cursor = self._get_conn().execute(sql, params)
        return [dict(row) for row in cursor.fetchall()]


# Singleton instance
_persistence = None

def get_persistence() -> HexStrikePersistence:
    """Get singleton persistence instance"""
    global _persistence
    if _persistence is None:
        _persistence = HexStrikePersistence()
    return _persistence
```

### 2.4 Implementation Tasks

- [ ] **1.1** Create `schemas/hexstrike_db.sql`
- [ ] **1.2** Create `hexstrike_persistence.py`
- [ ] **1.3** Create `data/` directory structure
- [ ] **1.4** Add persistence API endpoints to server (NEW routes only)
- [ ] **1.5** Add persistence MCP tools (NEW tools only)
- [ ] **1.6** Write unit tests

---

## 3. Phase 2: Checkpoint System

### 3.1 Integration with Existing Process Manager

The checkpoint system will **wrap** the existing `EnhancedProcessManager` and `execute_command_with_recovery()` function.

```python
# File: hexstrike_checkpoint.py
"""
Checkpoint system that wraps existing command execution.
Does NOT modify EnhancedProcessManager or execute_command_with_recovery.
"""

import asyncio
import time
from typing import Callable, Optional, Dict, Any
from hexstrike_persistence import get_persistence


class CheckpointExecutor:
    """
    Wraps existing command execution with checkpoint capability.
    Calls existing functions, adds checkpointing around them.
    """

    def __init__(self, checkpoint_interval: int = 30):
        self.checkpoint_interval = checkpoint_interval
        self.persistence = get_persistence()

    async def execute_with_checkpoints(
        self,
        scan_id: str,
        execute_fn: Callable,
        *args,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute a function with periodic checkpointing.

        Args:
            scan_id: ID of the scan (from persistence layer)
            execute_fn: The existing execution function to call
            *args, **kwargs: Arguments for execute_fn
        """
        last_checkpoint = time.time()
        output_buffer = []

        # Wrapper to capture output
        original_result = None
        checkpoint_state = {'args': args, 'kwargs': kwargs, 'started': time.time()}

        try:
            # Start checkpoint loop in background
            async def checkpoint_loop():
                nonlocal last_checkpoint
                while original_result is None:
                    await asyncio.sleep(self.checkpoint_interval)
                    if original_result is None:
                        progress = self._estimate_progress(output_buffer)
                        self.persistence.save_checkpoint(
                            scan_id=scan_id,
                            state=checkpoint_state,
                            output_snapshot=''.join(str(x) for x in output_buffer),
                            progress=progress
                        )
                        last_checkpoint = time.time()

            # Run checkpoint loop and execution concurrently
            checkpoint_task = asyncio.create_task(checkpoint_loop())

            # Call the EXISTING execution function
            original_result = await asyncio.get_event_loop().run_in_executor(
                None, lambda: execute_fn(*args, **kwargs)
            )

            # Cancel checkpoint loop
            checkpoint_task.cancel()

            return original_result

        except Exception as e:
            # Save final checkpoint on error
            self.persistence.save_checkpoint(
                scan_id=scan_id,
                state={**checkpoint_state, 'error': str(e)},
                output_snapshot=''.join(str(x) for x in output_buffer),
                progress=self._estimate_progress(output_buffer)
            )
            raise

    def resume_from_checkpoint(self, scan_id: str) -> Optional[Dict]:
        """Get checkpoint data to resume a scan"""
        checkpoint = self.persistence.get_latest_checkpoint(scan_id)
        if checkpoint:
            return {
                'state': checkpoint['state'],
                'output_so_far': checkpoint['output_snapshot'],
                'progress': checkpoint['progress'],
                'checkpoint_time': checkpoint['created_at']
            }
        return None

    def _estimate_progress(self, output: list) -> int:
        """Estimate progress based on output (simple heuristic)"""
        if not output:
            return 0
        # Simple line-based estimate
        lines = len(output)
        # Cap at 95% (100% only on completion)
        return min(95, lines)


class ResilientScanWrapper:
    """
    High-level wrapper for resilient scan execution.
    Uses existing HexStrike execution but adds persistence.
    """

    def __init__(self):
        self.persistence = get_persistence()
        self.checkpoint_executor = CheckpointExecutor()

    def start_scan(self, project_id: str, tool: str, command: str,
                   parameters: dict = None, session_id: str = None) -> str:
        """Start a tracked scan"""
        return self.persistence.start_scan(
            project_id=project_id,
            tool=tool,
            command=command,
            parameters=parameters,
            session_id=session_id
        )

    def complete_scan(self, scan_id: str, result: dict):
        """Record scan completion"""
        self.persistence.complete_scan(
            scan_id=scan_id,
            stdout=result.get('stdout', ''),
            stderr=result.get('stderr', ''),
            return_code=result.get('return_code', -1),
            execution_time=result.get('execution_time', 0),
            recovery_info=result.get('recovery_info')
        )

    def can_resume(self, scan_id: str) -> bool:
        """Check if a scan can be resumed"""
        scan = self.persistence.get_scan(scan_id)
        if not scan:
            return False
        return scan['status'] == 'running' and self.checkpoint_executor.resume_from_checkpoint(scan_id) is not None

    def get_resume_data(self, scan_id: str) -> Optional[Dict]:
        """Get data needed to resume a scan"""
        scan = self.persistence.get_scan(scan_id)
        checkpoint = self.checkpoint_executor.resume_from_checkpoint(scan_id)
        if scan and checkpoint:
            return {
                'scan': scan,
                'checkpoint': checkpoint,
                'tool': scan['tool'],
                'command': scan['command'],
                'parameters': scan['parameters']
            }
        return None
```

### 3.2 Implementation Tasks

- [ ] **2.1** Create `hexstrike_checkpoint.py`
- [ ] **2.2** Add checkpoint API endpoints
- [ ] **2.3** Add resume MCP tools
- [ ] **2.4** Test with long-running scans
- [ ] **2.5** Test simulated disconnections

---

## 4. Phase 3: RAG Integration

### 4.1 Vector Database (Complements Existing CVE System)

The RAG system will **add** semantic search capability alongside the existing `CVEIntelligenceManager`.

```python
# File: hexstrike_rag.py
"""
RAG system for HexStrike.
ADDS semantic search - does not replace existing CVE system.
"""

import json
from typing import List, Dict, Optional, Any
from pathlib import Path

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

    def __init__(self, data_dir: str = "data/rag"):
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

        self.client = chromadb.Client(Settings(
            chroma_db_impl="duckdb+parquet",
            persist_directory=str(self.data_dir / "chroma"),
            anonymized_telemetry=False
        ))

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

    def _init_embeddings(self):
        """Initialize embedding model"""
        if not EMBEDDINGS_AVAILABLE:
            return

        # Use lightweight model for speed
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')

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
            parts.append(f"Evidence: {finding['evidence'][:500]}")
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
            sev = f.get('metadata', {}).get('severity', 'unknown')
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
```

### 4.2 Implementation Tasks

- [ ] **3.1** Create `hexstrike_rag.py`
- [ ] **3.2** Add RAG dependencies to requirements
- [ ] **3.3** Add RAG API endpoints
- [ ] **3.4** Add automatic finding indexing (hook into save_finding)
- [ ] **3.5** Add context enrichment to MCP responses
- [ ] **3.6** Test semantic search accuracy

---

## 5. Phase 4: Token Optimization

### 5.1 Response Optimizer (Post-Processing)

```python
# File: hexstrike_optimizer.py
"""
Token optimization for HexStrike responses.
Post-processes responses without modifying existing output generation.
"""

from typing import Dict, Any, List, Optional
import json
import re


class ResponseOptimizer:
    """
    Optimizes responses to reduce token usage.
    Works as a post-processor on existing responses.
    """

    # Response detail tiers
    TIERS = {
        'minimal': {
            'max_stdout_lines': 10,
            'max_findings': 3,
            'include_raw': False,
            'include_evidence': False
        },
        'summary': {
            'max_stdout_lines': 50,
            'max_findings': 10,
            'include_raw': False,
            'include_evidence': True
        },
        'detailed': {
            'max_stdout_lines': 200,
            'max_findings': 50,
            'include_raw': True,
            'include_evidence': True
        },
        'full': {
            'max_stdout_lines': None,
            'max_findings': None,
            'include_raw': True,
            'include_evidence': True
        }
    }

    def optimize_response(self, response: Dict, tier: str = 'summary') -> Dict:
        """
        Optimize response based on tier level.
        Does not modify original response, returns optimized copy.
        """
        config = self.TIERS.get(tier, self.TIERS['summary'])
        optimized = response.copy()

        # Truncate stdout
        if 'stdout' in optimized and config['max_stdout_lines']:
            optimized['stdout'] = self._truncate_output(
                optimized['stdout'],
                config['max_stdout_lines']
            )

        # Limit findings
        if 'findings' in optimized and config['max_findings']:
            optimized['findings'] = optimized['findings'][:config['max_findings']]
            if len(response.get('findings', [])) > config['max_findings']:
                optimized['findings_truncated'] = True
                optimized['total_findings'] = len(response['findings'])

        # Remove raw data if not needed
        if not config['include_raw']:
            optimized.pop('raw_output', None)
            optimized.pop('raw_data', None)

        return optimized

    def _truncate_output(self, output: str, max_lines: int) -> str:
        """Truncate output to max lines"""
        if not output:
            return output

        lines = output.split('\n')
        if len(lines) <= max_lines:
            return output

        # Keep first and last portions
        head = lines[:max_lines // 2]
        tail = lines[-(max_lines // 2):]
        truncated = len(lines) - max_lines

        return '\n'.join(head) + f'\n\n... [{truncated} lines truncated] ...\n\n' + '\n'.join(tail)

    def compress_findings(self, findings: List[Dict], max_tokens: int = 500) -> str:
        """Compress findings list to summary text"""
        if not findings:
            return "No findings."

        # Group by severity
        by_severity = {}
        for f in findings:
            sev = f.get('severity', 'UNKNOWN')
            by_severity.setdefault(sev, []).append(f)

        lines = []
        token_estimate = 0

        for sev in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO']:
            if sev not in by_severity:
                continue

            for finding in by_severity[sev]:
                line = f"[{sev}] {finding.get('title', 'Unknown')}"
                if finding.get('location'):
                    line += f" @ {finding['location']}"

                # Rough token estimate (words * 1.3)
                tokens = len(line.split()) * 1.3
                if token_estimate + tokens > max_tokens:
                    lines.append(f"... and {len(findings) - len(lines)} more")
                    break

                lines.append(line)
                token_estimate += tokens

        return '\n'.join(lines)

    def create_incremental_update(self, previous: Dict, current: Dict) -> Dict:
        """
        Create incremental update (only changed data).
        Reduces tokens when context hasn't changed much.
        """
        if not previous:
            return current

        delta = {'_type': 'incremental'}

        for key, value in current.items():
            if key not in previous:
                delta[key] = value
            elif previous[key] != value:
                if isinstance(value, list) and isinstance(previous.get(key), list):
                    # For lists, only include new items
                    prev_set = set(json.dumps(x, sort_keys=True) for x in previous[key])
                    new_items = [x for x in value if json.dumps(x, sort_keys=True) not in prev_set]
                    if new_items:
                        delta[f'{key}_new'] = new_items
                        delta[f'{key}_count'] = len(value)
                else:
                    delta[key] = value

        return delta


class ContextManager:
    """
    Manages context to minimize repetition across requests.
    """

    def __init__(self):
        self.session_contexts = {}  # session_id -> context

    def get_context(self, session_id: str) -> Dict:
        """Get current context for session"""
        return self.session_contexts.get(session_id, {})

    def update_context(self, session_id: str, updates: Dict):
        """Update session context"""
        if session_id not in self.session_contexts:
            self.session_contexts[session_id] = {}
        self.session_contexts[session_id].update(updates)

    def get_context_summary(self, session_id: str, max_tokens: int = 200) -> str:
        """Get compressed context summary"""
        context = self.get_context(session_id)
        if not context:
            return "No previous context."

        summary_parts = []
        token_estimate = 0

        if 'target' in context:
            summary_parts.append(f"Target: {context['target']}")

        if 'technologies' in context:
            techs = context['technologies'][:5]  # Top 5
            summary_parts.append(f"Technologies: {', '.join(techs)}")

        if 'findings_count' in context:
            summary_parts.append(f"Findings: {context['findings_count']} total")

        return ' | '.join(summary_parts)

    def clear_context(self, session_id: str):
        """Clear session context"""
        self.session_contexts.pop(session_id, None)


# Singleton instances
_optimizer = None
_context_manager = None

def get_optimizer() -> ResponseOptimizer:
    global _optimizer
    if _optimizer is None:
        _optimizer = ResponseOptimizer()
    return _optimizer

def get_context_manager() -> ContextManager:
    global _context_manager
    if _context_manager is None:
        _context_manager = ContextManager()
    return _context_manager
```

### 5.2 Implementation Tasks

- [ ] **4.1** Create `hexstrike_optimizer.py`
- [ ] **4.2** Add tier parameter to MCP tools
- [ ] **4.3** Implement automatic context compression
- [ ] **4.4** Add incremental update support
- [ ] **4.5** Measure token reduction

---

## 6. Implementation Safety

### 6.1 Rules to Prevent Breaking Changes

1. **Never modify existing class methods** - only add new methods
2. **Never change existing API response formats** - add new fields, don't remove
3. **Never modify existing MCP tool signatures** - add new tools instead
4. **All new imports must be optional** - graceful degradation if missing
5. **New features must be disabled by default** - opt-in activation

### 6.2 Graceful Degradation

```python
# Pattern for all new modules:

try:
    import chromadb
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False

class HexStrikeRAG:
    def __init__(self):
        if not RAG_AVAILABLE:
            self.enabled = False
            return
        # Normal initialization

    def search(self, query):
        if not self.enabled:
            return []  # Return empty, don't crash
        # Normal search
```

### 6.3 Testing Checklist

Before merging any changes:

- [ ] All existing MCP tools still work
- [ ] All existing API endpoints return same format
- [ ] Server starts without new dependencies installed
- [ ] Cache still works (AdvancedCache)
- [ ] Error recovery still works (IntelligentErrorHandler)
- [ ] Workflows still execute (BugBountyWorkflowManager)

---

## 7. API Additions

### New Endpoints Only (Existing Unchanged)

```python
# Add to hexstrike_server.py (at end of file)

# ========== PROJECT MANAGEMENT (NEW) ==========
@app.route('/api/v2/projects', methods=['POST'])
@app.route('/api/v2/projects', methods=['GET'])
@app.route('/api/v2/projects/<project_id>', methods=['GET', 'PUT', 'DELETE'])

# ========== SESSION MANAGEMENT (NEW) ==========
@app.route('/api/v2/projects/<project_id>/sessions', methods=['POST', 'GET'])
@app.route('/api/v2/sessions/<session_id>', methods=['GET'])
@app.route('/api/v2/sessions/<session_id>/end', methods=['PUT'])

# ========== SCAN PERSISTENCE (NEW) ==========
@app.route('/api/v2/scans/<scan_id>', methods=['GET'])
@app.route('/api/v2/scans/<scan_id>/resume', methods=['POST'])
@app.route('/api/v2/scans/incomplete', methods=['GET'])

# ========== FINDINGS (NEW) ==========
@app.route('/api/v2/projects/<project_id>/findings', methods=['GET'])
@app.route('/api/v2/findings/search', methods=['GET'])

# ========== RAG (NEW) ==========
@app.route('/api/v2/rag/query', methods=['POST'])
@app.route('/api/v2/rag/context', methods=['POST'])
@app.route('/api/v2/rag/similar/<finding_id>', methods=['GET'])
```

Note: Using `/api/v2/` prefix to clearly separate from existing `/api/` endpoints.

---

## 8. File Changes

### New Files to Create

| File | Purpose | Priority |
|------|---------|----------|
| `schemas/hexstrike_db.sql` | Database schema | P1 |
| `hexstrike_persistence.py` | Persistence layer | P1 |
| `hexstrike_checkpoint.py` | Checkpoint system | P1 |
| `hexstrike_rag.py` | RAG/vector search | P2 |
| `hexstrike_optimizer.py` | Token optimization | P2 |
| `data/.gitkeep` | Data directory | P1 |

### Files to Modify (Append Only)

| File | Changes | Risk |
|------|---------|------|
| `hexstrike_server.py` | Add new endpoints at end | LOW |
| `hexstrike_mcp.py` | Add new MCP tools at end | LOW |
| `requirements.txt` | Add optional dependencies | LOW |

### Dependencies to Add

```txt
# Optional - graceful degradation if not installed
chromadb>=0.4.0
sentence-transformers>=2.2.0
```

---

## 9. Implementation Order

```
Week 1:
├── Day 1-2: Create schemas/hexstrike_db.sql
├── Day 3-4: Create hexstrike_persistence.py
└── Day 5: Add persistence API endpoints

Week 2:
├── Day 1-2: Create hexstrike_checkpoint.py
├── Day 3: Add checkpoint API endpoints
└── Day 4-5: Testing and fixes

Week 3:
├── Day 1-3: Create hexstrike_rag.py
├── Day 4: Add RAG API endpoints
└── Day 5: Integration testing

Week 4:
├── Day 1-2: Create hexstrike_optimizer.py
├── Day 3: Add optimization to MCP
└── Day 4-5: Final testing & documentation
```

---

## 10. Success Metrics

| Metric | Before | Target |
|--------|--------|--------|
| Data loss on disconnect | 100% | <10% |
| Scan resume capability | 0% | 95%+ |
| Finding retrieval (semantic) | None | <500ms |
| Token usage per session | Baseline | -40% |

---

## Appendix: Existing Code References

For implementers, key existing classes to understand (but NOT modify):

| Class | Location | Purpose |
|-------|----------|---------|
| `AdvancedCache` | `hexstrike_server.py:5085` | In-memory caching |
| `IntelligentErrorHandler` | `hexstrike_server.py:1606` | Error recovery |
| `IntelligentDecisionEngine` | `hexstrike_server.py:572` | Tool selection |
| `TargetProfile` | `hexstrike_server.py:474` | Target data model |
| `AttackChain` | `hexstrike_server.py:522` | Workflow state |
| `CVEIntelligenceManager` | `hexstrike_server.py:5750` | CVE knowledge |
| `BugBountyWorkflowManager` | `hexstrike_server.py:2447` | BB workflows |
| `CTFWorkflowManager` | `hexstrike_server.py:2795` | CTF workflows |

---

*Document maintained by HexStrike AI Team*
*Last updated: 2025-12-05 - Focused on missing features only*
