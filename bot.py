# bot.py
import discord
from discord.ext import commands
import sqlite3
import logging
import datetime
import re
from dateutil.parser import parse

bot = commands.Bot(command_prefix="/")
logging.basicConfig(level=logging.INFO)


def get_db():
    conn = sqlite3.connect("prediction_markets.db")
    return con


@bot.event
async def on_ready():
    logging.info(f"Logged in as {bot.user.name}")


@bot.command()
async def create_market(ctx, name: str):
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO markets (name, creator_id) VALUES (?, ?)",
            (name, ctx.author.id),
        )
        market_id = cursor.lastrowid
        conn.commit()
        await ctx.send(f"Market created with ID: {market_id}")
    except Exception as e:
        logging.error(f"Error creating market: {str(e)}")
        conn.rollback()
        await ctx.send("An error occurred while creating the market.")
    finally:
        conn.close()


@bot.command()
async def order(
    ctx,
    order_type: str,
    order_direction: str,
    market_id: int,
    quantity: int,
    price: str,
    duration: str = None,
):
    try:
        conn = get_db()
        cursor = conn.cursor()

        price_cents = int(decimal.Decimal(price) * 100)

        # Parse the duration and calculate the expiration timestamp
        expires_at = None

        if order_type == "market":
            if order_direction == "buy":
                price_cents = 99999999999999  # infinity
            else:
                price_cents = 0  # prices cannot go negative sorry :(
            expires_at = datetime(1970, 1, 1)
        else:
            if duration:
                try:
                    # Check if the duration is in the format of +1y3m3w9d3h45m3s
                    if duration.startswith("+"):
                        relative_duration = duration[1:]
                        expires_at = dateparser.parse(f"now + {relative_duration}")
                        if expires_at is None:
                            raise ValueError("Invalid relative duration format")
                    # Check if the duration is in the format of an ISO date (e.g., 2023-04-03)
                    else:
                        expires_at = dateparser.parse(duration)
                        if expires_at is None:
                            raise ValueError("Invalid ISO date format")
                        if expires_at.time() == datetime.time(0, 0, 0):
                            expires_at = expires_at.replace(
                                hour=23, minute=59, second=59
                            )
                except ValueError as e:
                    await ctx.send(
                        f"Invalid duration format: {str(e)}. Please provide a valid relative duration (e.g., +1y3m3w9d3h45m3s) or an ISO date (e.g., 2023-04-03)."
                    )
                    return
        # Begin a transaction
        cursor.execute("BEGIN TRANSACTION")

        # Check if the market exists
        cursor.execute("SELECT id FROM markets WHERE id = ?", (market_id,))
        market = cursor.fetchone()
        if not market:
            await ctx.send(f"Market with ID {market_id} does not exist.")
            cursor.execute("ROLLBACK")
            return

        # Insert the order into the orders table
        cursor.execute(
            """
            INSERT INTO orders (market_id, user_id, order_type, order_direction, price_cents, quantity, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (
                market_id,
                ctx.author.id,
                order_type,
                order_direction,
                price_cents,
                quantity,
                expires_at,
            ),
        )
        order_id = cursor.lastrowid

        # Match the order with existing opposite orders
        if order_direction == "buy":
            cursor.execute(
                """
                SELECT id,
                    price_cents,
                    quantity,
                    user_id
                FROM orders
                WHERE market_id = ?
                    AND order_direction = 'sell'
                    AND price_cents >= ?
                    AND (
                        expires_at IS NULL
                        OR expires_at > CURRENT_TIMESTAMP
                    )
                ORDER BY price_cents ASC,
                    created_at ASC
            """,
                (market_id, price_cents),
            )
        else:
            cursor.execute(
                """
                SELECT id,
                    price_cents,
                    quantity,
                    user_id
                FROM orders
                WHERE market_id = ?
                    AND order_direction = 'buy'
                    AND price_cents >= ?
                    AND (
                        expires_at IS NULL
                        OR expires_at > CURRENT_TIMESTAMP
                    )
                ORDER BY price_cents DESC,
                    created_at ASC
            """,
                (market_id, price_cents),
            )

        matching_orders = cursor.fetchall()

        for matching_order in matching_orders:
            (
                matching_order_id,
                matching_order_price_cents,
                matching_order_quantity,
                matching_user_id,
            ) = matching_order

            if quantity <= 0:
                break

            trade_quantity = min(quantity, matching_order_quantity)
            cursor.execute(
                """
                INSERT INTO trades (market_id, buyer_id, seller_id, price_cents, quantity)
                VALUES (?, ?, ?, ?, ?)
            """,
                (
                    market_id,
                    ctx.author.id if order_direction == "buy" else matching_user_id,
                    matching_user_id if order_direction == "buy" else ctx.author.id,
                    matching_order_price_cents,
                    trade_quantity,
                ),
            )

            quantity -= trade_quantity
            cursor.execute(
                "UPDATE orders SET quantity = quantity - ? WHERE id = ?",
                (trade_quantity, matching_order_id),
            )
        # delete the order if it is a market order
        if order_type == "market":
            cursor.execute("DELETE from ORDERS where id = ?", order_id)

        conn.commit()
        await ctx.send("Order placed successfully")
    except Exception as e:
        logging.error(f"Error placing order: {str(e)}")
        conn.rollback()
        await ctx.send("An error occurred while placing the order.")
    finally:
        conn.close()


@bot.command()
async def cancel_order(ctx, order_id: int):
    try:
        conn = get_db()
        cursor = conn.cursor()

        # Begin a transaction
        cursor.execute("BEGIN TRANSACTION")

        # Check if the order exists and belongs to the user
        cursor.execute(
            "SELECT id FROM orders WHERE id = ? AND user_id = ?",
            (order_id, ctx.author.id),
        )
        order = cursor.fetchone()
        if not order:
            await ctx.send(
                f"Order with ID {order_id} does not exist or does not belong to you."
            )
            cursor.execute("ROLLBACK")
            return

        # Delete the order from the orders table
        cursor.execute("DELETE FROM orders WHERE id = ?", (order_id,))

        conn.commit()
        await ctx.send("Order cancelled successfully")
    except Exception as e:
        logging.error(f"Error cancelling order: {str(e)}")
        conn.rollback()
        await ctx.send("An error occurred while cancelling the order.")
    finally:
        conn.close()


bot.run("YOUR_BOT_TOKEN")
