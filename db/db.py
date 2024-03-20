import logging
import sqlite3
from typing import List, Literal, Optional

from .objects import Market, Order, Trade


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
