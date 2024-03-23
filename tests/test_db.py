import sqlite3

from db import Database
from db.objects import User


def memory_conn() -> sqlite3.Connection:
    """
    Return a connection to an in-memory database with the schema loaded.
    """
    conn = sqlite3.connect(":memory:")
    with open("db/ddl.sql") as f:
        conn.executescript(f.read())
    return conn


def test_cascade():
    with Database(memory_conn()) as d:
        d.upsert_user(discord_id=1, display_name="A", avatar_hash="1")
        d.create_market(name="A", creator_id=1, criteria="")
        d.create_market(name="B", creator_id=1, criteria="cond")
        d.create_order(
            market_id=1,
            creator_id=1,
            order_type="market",
            order_direction="buy",
            price_cents=1,
            quantity=1,
            expires_at=1.0,
        )
        d.create_trade(market_id=1, buyer_id=1, seller_id=1, price_cents=1, quantity=1)
        d.create_trade(market_id=2, buyer_id=1, seller_id=1, price_cents=1, quantity=1)

        d.delete_market(market_id=2)
        assert len(d.get_markets()) == 1
        assert len(d.get_orders()) == 1
        assert len(d.get_trades()) == 1

        d.delete_market(market_id=1)
        assert len(d.get_markets()) == 0
        assert len(d.get_orders()) == 0
        assert len(d.get_trades()) == 0


def test_rollback():
    conn = memory_conn()

    try:
        with Database(conn) as d:
            d.upsert_user(discord_id=1, display_name="A", avatar_hash="1")
            d.create_market(name="A", creator_id=1, criteria="")
            d.commit()
            d.create_market(name="A", creator_id=1, criteria="")
            _ = 1 / 0
    except ZeroDivisionError:
        pass

    with Database(conn) as d:
        assert len(d.get_markets()) == 1


def test_user_upsert():
    with Database(memory_conn()) as d:
        d.upsert_user(discord_id=1, display_name="A", avatar_hash="1")
        d.upsert_user(discord_id=1, display_name="B", avatar_hash="2")
        users = d.get_users()
        assert len(users) == 1
        assert users[0] == User(id=1, display_name="B", avatar_hash="2")
