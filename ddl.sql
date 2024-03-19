CREATE TABLE IF NOT EXISTS markets (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    creator_id TEXT NOT NULL,
    created_atREAL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    market_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    order_type TEXT NOT NULL,
    order_direction TEXT NOT NULL,
    price_cents INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    created_at REAL DEFAULT CURRENT_TIMESTAMP,
    expires_at REAL,
    FOREIGN KEY (market_id) REFERENCES markets (id)
);
CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    market_id INTEGER NOT NULL,
    buyer_order_id INTEGER NOT NULL,
    seller_order_id INTEGER NOT NULL,
    price_cents INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    timestamp REAL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (market_id) REFERENCES markets (id),
    FOREIGN KEY (buyer_order_id) REFERENCES orders (id),
    FOREIGN KEY (seller_order_id) REFERENCES orders (id)
);