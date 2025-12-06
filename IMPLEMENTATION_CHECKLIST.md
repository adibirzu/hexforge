# HexStrike Enhancement - Implementation Checklist v2.1

## Focused on Missing Features Only

**Updated:** 2025-12-05 (After codebase comparison)

---

## What Already Exists (DO NOT DUPLICATE)

| Feature | Existing Class | Line # |
|---------|---------------|--------|
| In-Memory Cache | `AdvancedCache` | 5085 |
| Error Recovery | `IntelligentErrorHandler` | 1606 |
| Retry Logic | Built into error handler | 1666 |
| Failure Fallbacks | `FailureRecoverySystem` | 4449 |
| Graceful Degradation | `GracefulDegradation` | 2201 |
| Rate Limiting | `RateLimitDetector` | 4344 |
| Process Management | `EnhancedProcessManager` | 5208 |
| CVE Intelligence | `CVEIntelligenceManager` | 5750 |
| Exploit Templates | `AIExploitGenerator` | 7027 |
| Vuln Correlation | `VulnerabilityCorrelator` | 8510 |
| Tech Detection | `TechnologyDetector` | 4223 |
| Bug Bounty Workflows | `BugBountyWorkflowManager` | 2447 |
| CTF Workflows | `CTFWorkflowManager` | 2795 |
| Attack Chains | `AttackChain` | 522 |
| Decision Engine | `IntelligentDecisionEngine` | 572 |
| Target Profiling | `TargetProfile` | 474 |

---

## What's MISSING (Implement These)

### Priority 1: Persistence Layer
```
[ ] 1.1 Create schemas/hexstrike_db.sql
[ ] 1.2 Create hexstrike_persistence.py
[ ] 1.3 Create data/ directory
[ ] 1.4 Add /api/v2/projects endpoints
[ ] 1.5 Add /api/v2/sessions endpoints
[ ] 1.6 Add MCP tools for projects/sessions
[ ] 1.7 Unit tests
```

### Priority 2: Checkpoint System
```
[ ] 2.1 Create hexstrike_checkpoint.py
[ ] 2.2 Add /api/v2/scans endpoints
[ ] 2.3 Add /api/v2/scans/{id}/resume endpoint
[ ] 2.4 Add MCP tools for scan resume
[ ] 2.5 Test with long-running scans
[ ] 2.6 Test simulated disconnections
```

### Priority 3: RAG Integration
```
[ ] 3.1 Create hexstrike_rag.py
[ ] 3.2 Add chromadb to requirements (optional)
[ ] 3.3 Add /api/v2/rag endpoints
[ ] 3.4 Hook RAG into save_finding()
[ ] 3.5 Add context enrichment
[ ] 3.6 Test semantic search
```

### Priority 4: Token Optimization
```
[ ] 4.1 Create hexstrike_optimizer.py
[ ] 4.2 Add response tier parameter
[ ] 4.3 Add incremental updates
[ ] 4.4 Measure token reduction
```

---

## Files to Create

| File | Purpose | Dependencies |
|------|---------|-------------|
| `schemas/hexstrike_db.sql` | Database schema | None |
| `hexstrike_persistence.py` | Project/session/scan storage | sqlite3 (builtin) |
| `hexstrike_checkpoint.py` | Checkpoint/resume | hexstrike_persistence |
| `hexstrike_rag.py` | Vector search | chromadb (optional) |
| `hexstrike_optimizer.py` | Token reduction | None |
| `data/.gitkeep` | Data directory marker | None |

---

## Files to Modify (APPEND ONLY)

### hexstrike_server.py
Add at END of file (after line ~17290):
```python
# ========== V2 API: PERSISTENCE LAYER ==========
# Add 15 new endpoints here
# DO NOT modify existing endpoints
```

### hexstrike_mcp.py
Add at END of file (after existing tools):
```python
# ========== V2 MCP TOOLS: PERSISTENCE ==========
# Add 10 new MCP tools here
# DO NOT modify existing tools
```

### requirements.txt
Add (as optional):
```
# Optional RAG dependencies
chromadb>=0.4.0
sentence-transformers>=2.2.0
```

---

## Directory Structure

```bash
# Run this to create needed directories:
mkdir -p /home/kali/Desktop/hexstrike-ai/data/projects
mkdir -p /home/kali/Desktop/hexstrike-ai/data/rag/chroma
mkdir -p /home/kali/Desktop/hexstrike-ai/schemas
touch /home/kali/Desktop/hexstrike-ai/data/.gitkeep
```

---

## New API Endpoints (v2 prefix)

```
# Project Management
POST   /api/v2/projects                    Create project
GET    /api/v2/projects                    List projects
GET    /api/v2/projects/{id}               Get project
PUT    /api/v2/projects/{id}               Update project
DELETE /api/v2/projects/{id}               Delete project

# Sessions
POST   /api/v2/projects/{id}/sessions      Start session
GET    /api/v2/projects/{id}/sessions      List sessions
GET    /api/v2/sessions/{id}               Get session
PUT    /api/v2/sessions/{id}/end           End session

# Scans with Persistence
GET    /api/v2/scans/{id}                  Get scan details
POST   /api/v2/scans/{id}/resume           Resume scan
GET    /api/v2/scans/incomplete            List resumable scans

# Findings
GET    /api/v2/projects/{id}/findings      Get findings
GET    /api/v2/findings/search             Search findings

# RAG
POST   /api/v2/rag/query                   Query knowledge
POST   /api/v2/rag/context                 Get enriched context
GET    /api/v2/rag/similar/{finding_id}    Find similar
```

---

## New MCP Tools

```python
# Project/Session Tools
@mcp.tool() create_project(name, target, description)
@mcp.tool() list_projects()
@mcp.tool() get_project(project_id)
@mcp.tool() start_session(project_id)
@mcp.tool() end_session(session_id)

# Resilience Tools
@mcp.tool() get_scan_status(scan_id)
@mcp.tool() resume_scan(scan_id)
@mcp.tool() list_incomplete_scans(project_id)

# RAG Tools
@mcp.tool() query_knowledge(query)
@mcp.tool() find_similar_findings(finding_id)
@mcp.tool() get_target_context(target, project_id)
```

---

## Safety Rules

1. **APPEND ONLY** - Never modify existing code
2. **NEW ENDPOINTS** use `/api/v2/` prefix
3. **NEW TOOLS** added after existing tools
4. **OPTIONAL DEPS** - Graceful degradation if missing
5. **BACKWARDS COMPATIBLE** - Old API unchanged

---

## Quick Test Commands

```bash
# Test persistence
curl -X POST http://localhost:8888/api/v2/projects \
  -H "Content-Type: application/json" \
  -d '{"name":"Test","target":"example.com"}'

# Test existing (must still work)
curl http://localhost:8888/health
curl http://localhost:8888/api/tools/nmap -X POST \
  -H "Content-Type: application/json" \
  -d '{"target":"127.0.0.1"}'
```

---

## Verification Checklist

Before each commit, verify:

- [ ] `curl http://localhost:8888/health` returns healthy
- [ ] Existing `/api/tools/nmap` still works
- [ ] Server starts without chromadb installed
- [ ] No modifications to existing class methods
- [ ] All new code in separate files or appended

---

## Token Savings Estimate

| Feature | Reduction |
|---------|-----------|
| RAG context retrieval | 30-40% |
| Incremental updates | 15-20% |
| Response tiers | 10-15% |
| **Total Expected** | **40-50%** |

---

## Start Implementation

```bash
# Step 1: Create directory structure
cd /home/kali/Desktop/hexstrike-ai
mkdir -p data/projects data/rag/chroma schemas

# Step 2: Create database schema
# Edit: schemas/hexstrike_db.sql

# Step 3: Create persistence layer
# Edit: hexstrike_persistence.py

# Step 4: Test persistence independently
python3 -c "from hexstrike_persistence import get_persistence; p = get_persistence(); print('OK')"

# Step 5: Add server endpoints
# Append to: hexstrike_server.py

# Step 6: Add MCP tools
# Append to: hexstrike_mcp.py

# Step 7: Test full system
./start_server_network.sh
curl http://localhost:8888/api/v2/projects
```

---

*Last updated: 2025-12-05 - Removed duplicate features*
