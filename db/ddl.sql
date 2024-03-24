CREATE TABLE IF NOT EXISTS markets
(
    id           INTEGER PRIMARY KEY,
    name         TEXT    NOT NULL,
    creator_id   INTEGER NOT NULL,
    created_at   INTEGER DEFAULT (CAST(strftime('%s', 'now') AS INTEGER) * 1000),
    criteria     TEXT    NOT NULL,
    payout_cents INTEGER,
    resolved_at  INTEGER,
    FOREIGN KEY (creator_id) REFERENCES users (id)
);

CREATE TABLE IF NOT EXISTS orders
(
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    market_id       INTEGER NOT NULL,
    creator_id      INTEGER NOT NULL,
    order_type      TEXT    NOT NULL,
    order_direction TEXT    NOT NULL,
    price_cents     INTEGER NOT NULL,
    quantity        INTEGER NOT NULL,
    created_at      INTEGER DEFAULT (CAST(strftime('%s', 'now') AS INTEGER) * 1000),
    expires_at      INTEGER,
    FOREIGN KEY (market_id) REFERENCES markets (id) ON DELETE CASCADE,
    FOREIGN KEY (creator_id) REFERENCES users (id)
);

CREATE TABLE IF NOT EXISTS trades
(
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    market_id   INTEGER NOT NULL,
    buyer_id    INTEGER NOT NULL,
    seller_id   INTEGER NOT NULL,
    price_cents INTEGER NOT NULL,
    quantity    INTEGER NOT NULL,
    timestamp   INTEGER DEFAULT (CAST(strftime('%s', 'now') AS INTEGER) * 1000),
    FOREIGN KEY (market_id) REFERENCES markets (id) ON DELETE CASCADE,
    FOREIGN KEY (buyer_id) REFERENCES users (id),
    FOREIGN KEY (seller_id) REFERENCES users (id)
);

CREATE TABLE IF NOT EXISTS users
(
    id           INTEGER PRIMARY KEY,
    display_name TEXT,
    avatar_hash  TEXT
);

CREATE TRIGGER delete_orders_with_zero_quantity
    AFTER
        UPDATE OF quantity
    ON orders
BEGIN
    DELETE
    FROM orders
    WHERE id = OLD.id
      AND quantity = 0;
END;

CREATE TRIGGER ensure_valid_market_id_orders
    BEFORE INSERT
    ON orders
BEGIN
    SELECT RAISE(ABORT, 'Invalid market_id')
    WHERE NEW.market_id NOT IN (SELECT id FROM markets);
END;

CREATE TRIGGER ensure_valid_market_id_trades
    BEFORE INSERT
    ON trades
BEGIN
    SELECT RAISE(ABORT, 'Invalid market_id')
    WHERE NEW.market_id NOT IN (SELECT id FROM markets);
END;
