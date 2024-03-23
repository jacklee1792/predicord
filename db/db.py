import logging
import sqlite3
from typing import List, Literal, Optional

from .objects import Market, Order, Trade, User


class Database:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.cursor: Optional[sqlite3.Cursor] = None

    def __enter__(self):
        self.cursor = self.conn.cursor()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is not None:
            self.conn.rollback()
            exc_info = (exc_type, exc_value, traceback)
            logging.warning("DB exception", exc_info=exc_info)
        else:
            self.conn.commit()

        # Deliberately remove the cursor, so it can't be reused without the context
        # manager
        self.cursor.close()
        self.cursor = None, None

    def commit(self):
        self.conn.commit()

    def create_market(self, name: str, creator_id: int, criteria: str) -> int:
        sql = "INSERT INTO markets (name, creator_id, criteria) VALUES (?, ?, ?)"
        self.cursor.execute(sql, (name, creator_id, criteria))
        return self.cursor.lastrowid

    def update_market(self, market_id: int, name: str, criteria: str) -> None:
        sql = "UPDATE markets SET name = ?, criteria = ? WHERE id = ?"
        self.cursor.execute(sql, (name, criteria, market_id))

    def get_market_by_id(self, market_id: int) -> Optional[Market]:
        sql = "SELECT * FROM markets WHERE id = ?"
        self.cursor.execute(sql, (market_id,))
        res = self.cursor.fetchone()
        return Market(*res) if res else None

    def get_markets(self) -> List[Market]:
        sql = "SELECT * FROM markets"
        self.cursor.execute(sql)
        markets = [Market(*m) for m in self.cursor.fetchall()]
        return markets

    def delete_market(self, market_id: int) -> None:
        sql = "DELETE FROM markets where id = ?"
        self.cursor.execute(sql, (market_id,))

    def create_order(
            self,
            market_id: int,
            creator_id: int,
            order_type: Literal["market", "limit"],
            order_direction: Literal["buy", "sell"],
            price_cents: int,
            quantity: int,
            expires_at: float,
    ) -> int:
        sql = (
            "INSERT INTO orders (market_id, creator_id, order_type, order_direction, "
            "price_cents, quantity, expires_at) VALUES (?, ?, ?, ?, ?, ?, ?)"
        )
        self.cursor.execute(
            sql,
            (
                market_id,
                creator_id,
                order_type,
                order_direction,
                price_cents,
                quantity,
                expires_at,
            ),
        )
        return self.cursor.lastrowid

    def get_orders(self) -> List[Order]:
        sql = "SELECT * FROM orders"
        self.cursor.execute(sql)
        orders = [Order(*o) for o in self.cursor.fetchall()]
        return orders

    def get_orders_by_market_id(self, market_id: int) -> List[Order]:
        sql = "SELECT * FROM orders WHERE market_id = ?"
        self.cursor.execute(sql, (market_id,))
        orders = [Order(*o) for o in self.cursor.fetchall()]
        return orders

    def delete_order(self, order_id: int) -> None:
        sql = "DELETE FROM orders where id = ?"
        self.cursor.execute(sql, (order_id,))

    def create_trade(
            self,
            market_id: int,
            buyer_id: int,
            seller_id: int,
            price_cents: int,
            quantity: int,
    ) -> int:
        sql = (
            "INSERT INTO trades (market_id, buyer_id, seller_id, price_cents, "
            "quantity) VALUES (?, ?, ?, ?, ?)"
        )
        self.cursor.execute(
            sql, (market_id, buyer_id, seller_id, price_cents, quantity)
        )
        return self.cursor.lastrowid

    def get_trades(self) -> List[Trade]:
        sql = "SELECT * FROM trades"
        self.cursor.execute(sql)
        trades = [Trade(*t) for t in self.cursor.fetchall()]
        return trades

    def delete_trade(self, trade_id: int) -> None:
        sql = "DELETE FROM trades where id = ?"
        self.cursor.execute(sql, (trade_id,))

    def upsert_user(self, discord_id: int, display_name: str, avatar_hash: str) -> int:
        sql = (
            "INSERT OR REPLACE INTO users (id, display_name, avatar_hash) VALUES ("
            "?, ?, ?)"
        )
        self.cursor.execute(sql, (discord_id, display_name, avatar_hash))
        return self.cursor.lastrowid

    def get_users(self) -> List[User]:
        sql = "SELECT * FROM users"
        self.cursor.execute(sql)
        users = [User(*u) for u in self.cursor.fetchall()]
        return users

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        sql = "SELECT * FROM users WHERE id = ?"
        self.cursor.execute(sql, (user_id,))
        res = self.cursor.fetchone()
        return User(*res) if res else None
