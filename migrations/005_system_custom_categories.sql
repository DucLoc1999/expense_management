-- migrate:up
ALTER TABLE categories ADD COLUMN user_id BIGINT REFERENCES telegram_users(tele_user_id);
ALTER TABLE categories ADD COLUMN parent_id INTEGER REFERENCES categories(id);
ALTER TABLE categories ADD COLUMN slug TEXT;
ALTER TABLE categories RENAME COLUMN is_default TO is_system;
ALTER TABLE categories DROP CONSTRAINT IF EXISTS categories_name_key;

CREATE UNIQUE INDEX categories_system_name_uq ON categories (name) WHERE user_id IS NULL;
CREATE UNIQUE INDEX categories_user_name_uq ON categories (user_id, name) WHERE user_id IS NOT NULL;

UPDATE categories SET is_system = TRUE WHERE is_system = FALSE;

UPDATE categories
SET slug = lower(btrim(regexp_replace(
    translate(lower(name),
        'áàảãạăắằẳẵặâấầẩẫậéèẻẽẹêếềểễệíìỉĩịóòỏõọôốồổỗộơớờởỡợúùủũụưứừửữựýỳỷỹỵđ',
        'aaaaaaaaaaaaaaaaaeeeeeeeeeeeiiiiiooooooooooooooooouuuuuuuuuuuyyyyyd'),
    '[^a-z0-9]+', '-', 'g'), '-'))
WHERE is_system = TRUE;

ALTER TABLE categories ADD CONSTRAINT categories_system_check CHECK (is_system = (user_id IS NULL));

-- migrate:down
ALTER TABLE categories DROP CONSTRAINT IF EXISTS categories_system_check;
DROP INDEX IF EXISTS categories_user_name_uq;
DROP INDEX IF EXISTS categories_system_name_uq;
ALTER TABLE categories DROP COLUMN IF EXISTS slug;
ALTER TABLE categories DROP COLUMN IF EXISTS parent_id;
ALTER TABLE categories DROP COLUMN IF EXISTS user_id;
ALTER TABLE categories RENAME COLUMN is_system TO is_default;
ALTER TABLE categories ADD CONSTRAINT categories_name_key UNIQUE (name);
