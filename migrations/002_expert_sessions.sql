-- migrate:up
CREATE TABLE IF NOT EXISTS expert_sessions (
    id SERIAL PRIMARY KEY,
    tele_user_id BIGINT NOT NULL,
    session_uuid TEXT UNIQUE NOT NULL,
    filter_start DATE,
    filter_end DATE,
    created_at TIMESTAMP DEFAULT NOW(),
    ended_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS expert_messages (
    id SERIAL PRIMARY KEY,
    session_id INT REFERENCES expert_sessions(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS expert_messages_session_idx ON expert_messages (session_id);

-- migrate:down
DROP TABLE IF EXISTS expert_messages;
DROP TABLE IF EXISTS expert_sessions;
