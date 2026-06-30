CREATE TABLE IF NOT EXISTS regulations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    title TEXT NOT NULL,
    url TEXT NOT NULL UNIQUE,
    published_at TEXT,
    full_text TEXT,
    hash TEXT NOT NULL UNIQUE,
    processed_at TEXT,
    opportunity_json TEXT,
    urgency_score INTEGER
);

CREATE INDEX IF NOT EXISTS idx_regulations_hash ON regulations(hash);
CREATE INDEX IF NOT EXISTS idx_regulations_processed ON regulations(processed_at);
CREATE INDEX IF NOT EXISTS idx_regulations_urgency ON regulations(urgency_score DESC);