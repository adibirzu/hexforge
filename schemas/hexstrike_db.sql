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
