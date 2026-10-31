"""SQLite table definitions: JSON documents preserve typed API/agent schemas."""
EVENT_TABLES = {'agent_plans','agent_observations','tool_executions','repository_snapshots','repository_files',
    'skill_claims','skill_evidence','test_results','git_findings','similarity_findings','viva_questions','viva_answers','approval_records'}

SCHEMA = [
    'CREATE TABLE IF NOT EXISTS baseline_records (assessment_id TEXT PRIMARY KEY, session_id TEXT NOT NULL, data TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP)',
    'CREATE TABLE IF NOT EXISTS evaluation_runs (evaluation_id TEXT PRIMARY KEY, data TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP)',
    'CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY, applied_at TEXT DEFAULT CURRENT_TIMESTAMP)',
    'CREATE TABLE IF NOT EXISTS candidates (id TEXT PRIMARY KEY)',
    'CREATE TABLE IF NOT EXISTS verification_sessions (id TEXT PRIMARY KEY, candidate_id TEXT NOT NULL REFERENCES candidates(id), status TEXT NOT NULL, data TEXT NOT NULL, updated_at TEXT DEFAULT CURRENT_TIMESTAMP)',
    'CREATE TABLE IF NOT EXISTS credentials (id TEXT PRIMARY KEY, session_id TEXT UNIQUE NOT NULL, data TEXT NOT NULL)',
]
for table in sorted(EVENT_TABLES):
    SCHEMA.append(f'CREATE TABLE IF NOT EXISTS {table} (id INTEGER PRIMARY KEY, session_id TEXT NOT NULL, data TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP)')
    SCHEMA.append(f'CREATE INDEX IF NOT EXISTS idx_{table}_session ON {table}(session_id)')
