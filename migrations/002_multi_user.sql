-- migrate:up
CREATE TABLE IF NOT EXISTS telegram_users (
    id SERIAL PRIMARY KEY,
    tele_user_id BIGINT UNIQUE NOT NULL,
    role TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMP DEFAULT NOW()
);

ALTER TABLE orders ADD COLUMN tele_user_id BIGINT NOT NULL DEFAULT 0;

-- migrate:down
ALTER TABLE orders DROP COLUMN IF EXISTS tele_user_id;
DROP TABLE IF EXISTS telegram_users;
