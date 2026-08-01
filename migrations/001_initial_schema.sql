-- migrate:up
CREATE TABLE IF NOT EXISTS categories (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    name_vi TEXT,
    is_system BOOLEAN NOT NULL DEFAULT TRUE,
    user_id BIGINT,
    parent_id INTEGER REFERENCES categories(id),
    created_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT categories_system_check CHECK (is_system = (user_id IS NULL))
);

CREATE UNIQUE INDEX categories_system_name_uq ON categories (name) WHERE user_id IS NULL;
CREATE UNIQUE INDEX categories_system_name_vi_uq ON categories (name_vi) WHERE user_id IS NULL AND name_vi IS NOT NULL;
CREATE UNIQUE INDEX categories_user_name_uq ON categories (user_id, name) WHERE user_id IS NOT NULL;

INSERT INTO categories (name, name_vi, is_system) VALUES
    ('Food & Drink', 'Ăn uống', TRUE),
    ('Household Goods', 'Đồ gia dụng', TRUE),
    ('Electronics', 'Điện tử', TRUE),
    ('Fashion', 'Thời trang', TRUE),
    ('Health & Beauty', 'Sức khỏe & Làm đẹp', TRUE),
    ('Office Supplies', 'Văn phòng phẩm', TRUE),
    ('Mom & Baby', 'Mẹ & Bé', TRUE),
    ('Pets', 'Thú cưng', TRUE),
    ('Sports', 'Thể thao', TRUE),
    ('Other', 'Khác', TRUE)
ON CONFLICT (name) WHERE user_id IS NULL DO NOTHING;

CREATE TABLE IF NOT EXISTS bills (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    money INTEGER NOT NULL,
    shop TEXT NOT NULL,
    date DATE NOT NULL,
    notes TEXT DEFAULT '',
    payment_source TEXT NOT NULL DEFAULT 'shopee',
    tele_user_id BIGINT NOT NULL DEFAULT 0,
    category_id INTEGER REFERENCES categories(id),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS telegram_users (
    id SERIAL PRIMARY KEY,
    tele_user_id BIGINT UNIQUE NOT NULL,
    name TEXT NOT NULL DEFAULT '',
    role TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMP DEFAULT NOW()
);

-- migrate:down
DROP TABLE IF EXISTS bills;
DROP TABLE IF EXISTS telegram_users;
DROP TABLE IF EXISTS categories;
