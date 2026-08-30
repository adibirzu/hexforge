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
import os

# TargetProfile / AttackChain from hexstrike_server are not imported here.
# save_target_profile duck-types the profile (to_dict / __dict__) so this
# module can load without pulling in the Flask server (circular import).


class HexStrikePersistence:
    """
    Persistence layer that WRAPS existing functionality.
    Does not replace AdvancedCache or any existing caching.
    """

    def __init__(self, db_path: str = None):
        if db_path is None:
            # Default to data directory in the same folder as this file
            base_dir = os.path.dirname(os.path.abspath(__file__))
            db_path = os.path.join(base_dir, "data", "hexstrike.db")
        
        self.db_path = db_path
        self._ensure_data_dir()
        self._init_db()
        self._local = threading.local()

    def _ensure_data_dir(self):
        """Create data directory if it doesn't exist"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

    def _get_conn(self):
        """Get thread-local database connection"""
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            try:
                self._local.conn = sqlite3.connect(self.db_path)
                self._local.conn.row_factory = sqlite3.Row
            except sqlite3.Error:
                # Fallback if connection fails
                return sqlite3.connect(self.db_path)
        return self._local.conn

    def _init_db(self):
        """Initialize database schema"""
        schema_path = Path(os.path.dirname(os.path.abspath(__file__))) / "schemas" / "hexstrike_db.sql"
        if schema_path.exists():
            conn = sqlite3.connect(self.db_path)
            with open(schema_path) as f:
                conn.executescript(f.read())
            conn.commit()
            conn.close()

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
        if profile is None:
            return
            
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
        row = cursor.fetchone()
        max_num = row[0] if row and row[0] is not None else 0

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
