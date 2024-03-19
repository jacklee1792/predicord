# bot.py
import discord
from discord.ext import commands
import sqlite3
import logging
import datetime

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
    price: float,
    quantity: int,
    duration: str = None,
):
    try:
        conn = get_db()
        cursor = conn.cursor()

        # Parse the duration and calculate the expiration timestamp
        expires_at = None
        if duration:
            try:
                duration_seconds = int(duration)
                expires_at = datetime.datetime.now() + datetime.timedelta(
                    seconds=duration_seconds
                )
            except ValueError:
                await ctx.send(
                    "Invalid duration format. Please provide duration in seconds."
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
            INSERT INTO orders (market_id, user_id, order_type, order_direction, price, quantity, remaining_quantity, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                market_id,
                ctx.author.id,
                order_type,
                order_direction,
                price,
                quantity,
                quantity,
                expires_at,
            ),
        )
        order_id = cursor.lastrowid

        # Match the order with existing opposite orders
        if order_direction == "buy":
            cursor.execute(
                """
                SELECT id, price, remaining_quantity
                FROM orders
                WHERE market_id = ? AND order_direction = 'sell' AND price <= ?
                ORDER BY price ASC, created_at ASC
            """,
                (market_id, price),
            )
        else:
            cursor.execute(
                """
                SELECT id, price, remaining_quantity
                FROM orders
                WHERE market_id = ? AND order_direction = 'buy' AND price >= ?
                ORDER BY price DESC, created_at ASC
            """,
                (market_id, price),
            )

        matching_orders = cursor.fetchall()

        for matching_order in matching_orders:
            matching_order_id, matching_order_price, matching_order_quantity = (
                matching_order
            )

            if quantity <= 0:
                break

            trade_quantity = min(quantity, matching_order_quantity)
            cursor.execute(
                """
                INSERT INTO trades (market_id, buyer_order_id, seller_order_id, price, quantity)
                VALUES (?, ?, ?, ?, ?)
            """,
                (
                    market_id,
                    order_id if order_direction == "buy" else matching_order_id,
                    matching_order_id if order_direction == "buy" else order_id,
                    matching_order_price,
                    trade_quantity,
                ),
            )

            quantity -= trade_quantity
            cursor.execute(
                "UPDATE orders SET remaining_quantity = remaining_quantity - ? WHERE id = ?",
                (trade_quantity, matching_order_id),
            )

        # Update the remaining quantity of the new order
        cursor.execute(
            "UPDATE orders SET remaining_quantity = ? WHERE id = ?",
            (quantity, order_id),
        )

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
