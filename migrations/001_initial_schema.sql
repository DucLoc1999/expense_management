-- migrate:up
CREATE TABLE IF NOT EXISTS categories (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    is_default BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    money INTEGER NOT NULL,
    shop TEXT NOT NULL,
    category_id INTEGER NOT NULL REFERENCES categories(id),
    date DATE NOT NULL,
    notes TEXT DEFAULT '',
    payment_source TEXT NOT NULL DEFAULT 'shopee',
    sheet_synced BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

INSERT INTO categories (name, is_default) VALUES
    ('Ăn uống', TRUE),
    ('Đồ gia dụng', TRUE),
    ('Điện tử', TRUE),
    ('Thời trang', TRUE),
    ('Sức khỏe & Làm đẹp', TRUE),
    ('Văn phòng phẩm', TRUE),
    ('Mẹ & Bé', TRUE),
    ('Thú cưng', TRUE),
    ('Thể thao', TRUE),
    ('Khác', TRUE)
ON CONFLICT (name) DO NOTHING;

-- migrate:down
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS categories;
