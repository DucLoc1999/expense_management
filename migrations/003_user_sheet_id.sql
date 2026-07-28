-- migrate:up
ALTER TABLE telegram_users ADD COLUMN IF NOT EXISTS sheet_id INTEGER;

-- migrate:down
ALTER TABLE telegram_users DROP COLUMN IF EXISTS sheet_id;
