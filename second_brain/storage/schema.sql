-- Second Brain SQLite schema (v1)

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS meta (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
  id TEXT PRIMARY KEY,
  started_at TEXT NOT NULL,
  ended_at TEXT,
  agent_id TEXT,
  project TEXT
);

CREATE TABLE IF NOT EXISTS events (
  id TEXT PRIMARY KEY,
  ts TEXT NOT NULL,
  type TEXT NOT NULL,
  title TEXT NOT NULL,
  details TEXT,
  project TEXT,
  outcome TEXT NOT NULL DEFAULT 'passed',
  tags_json TEXT NOT NULL DEFAULT '[]',
  session_id TEXT,
  agent_id TEXT,
  meta_json TEXT NOT NULL DEFAULT '{}',
  FOREIGN KEY(session_id) REFERENCES sessions(id)
);

CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts);
CREATE INDEX IF NOT EXISTS idx_events_project ON events(project);
CREATE INDEX IF NOT EXISTS idx_events_agent ON events(agent_id);
CREATE INDEX IF NOT EXISTS idx_events_session ON events(session_id);

CREATE TABLE IF NOT EXISTS credentials (
  id TEXT PRIMARY KEY,
  created_at TEXT NOT NULL,
  service TEXT NOT NULL,
  kind TEXT NOT NULL,
  context TEXT NOT NULL,
  value_enc TEXT NOT NULL,
  last_used TEXT,
  expires_at TEXT,
  rotation_note TEXT
);

CREATE INDEX IF NOT EXISTS idx_creds_service ON credentials(service);
CREATE INDEX IF NOT EXISTS idx_creds_kind ON credentials(kind);
