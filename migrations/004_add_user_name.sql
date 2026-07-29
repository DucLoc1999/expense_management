-- migrate:up
ALTER TABLE telegram_users ADD COLUMN IF NOT EXISTS name TEXT NOT NULL DEFAULT '';

-- migrate:down
ALTER TABLE telegram_users DROP COLUMN IF EXISTS name;
