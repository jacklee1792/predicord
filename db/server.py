from flask import Flask, request, session, jsonify
import sqlite3
import decimal
import logging
from datetime import datetime
import dateparser

app = Flask(__name__)
app.secret_key = "YOUR_SECRET_KEY"


@app.route("/order", methods=["POST"])
def order():
    data = request.get_json()
    order_type = data["order_type"]
    order_direction = data["order_direction"]
    market_id = data["market_id"]
    quantity = data["quantity"]
    price = data["price"]
    duration = data.get("duration")
    user_id = session["user_id"]

    # Function logic goes here
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
                    return (
                        jsonify(
                            {
                                "error": f"Invalid duration format: {str(e)}. Please provide a valid relative duration (e.g., +1y3m3w9d3h45m3s) or an ISO date (e.g., 2023-04-03)."
                            }
                        ),
                        400,
                    )
        # Begin a transaction
        cursor.execute("BEGIN TRANSACTION")

        # Check if the market exists
        cursor.execute("SELECT id FROM markets WHERE id = ?", (market_id,))
        market = cursor.fetchone()
        if not market:
            cursor.execute("ROLLBACK")
            return (
                jsonify({"error": f"Market with ID {market_id} does not exist."}),
                404,
            )

        # Insert the order into the orders table
        cursor.execute(
            """
            INSERT INTO orders (market_id, user_id, order_type, order_direction, price_cents, quantity, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (
                market_id,
                user_id,
                order_type,
                order_direction,
                price_cents,
                quantity,
                expires_at,
            ),
        )
        order_id = cursor.lastrowid

        matching_orders = get_matching_orders(cursor, order_direction, price_cents)

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
                    user_id if order_direction == "buy" else matching_user_id,
                    matching_user_id if order_direction == "buy" else user_id,
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
        return jsonify({"message": "Order placed successfully"})
    except Exception as e:
        logging.error(f"Error placing order: {str(e)}")
        conn.rollback()
        return jsonify({"error": "An error occurred while placing the order."}), 500
    finally:
        conn.close()


def get_matching_orders(cursor, order_direction, price_cents):
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


@app.route("/cancel_order", methods=["POST"])
def cancel_order():
    data = request.get_json()
    order_id = data["order_id"]
    user_id = session["user_id"]

    # Function logic goes here
    try:
        conn = get_db()
        cursor = conn.cursor()

        # Begin a transaction
        cursor.execute("BEGIN TRANSACTION")

        # Check if the order exists and belongs to the user
        cursor.execute(
            "SELECT id FROM orders WHERE id = ? AND user_id = ?",
            (order_id, user_id),
        )
        order = cursor.fetchone()
        if not order:
            cursor.execute("ROLLBACK")
            return (
                jsonify(
                    {
                        "error": f"Order with ID {order_id} does not exist or does not belong to you."
                    }
                ),
                404,
            )

        # Delete the order from the orders table
        cursor.execute("DELETE FROM orders WHERE id = ?", (order_id,))

        conn.commit()
        return jsonify({"message": "Order cancelled successfully"})
    except Exception as e:
        logging.error(f"Error cancelling order: {str(e)}")
        conn.rollback()
        return jsonify({"error": "An error occurred while cancelling the order."}), 500
    finally:
        conn.close()


@app.route("/pnl", methods=["GET"])
def pnl():
    user = request.args.get("user", "me")
    market = request.args.get("market", "all")
    user_id = session["user_id"]

    # Function logic goes here
    conn = sqlite3.connect("market.db")
    c = conn.cursor()

    if user == "me":
        user_id = user_id
    elif user.startswith("<@") and user.endswith(">"):
        user_id = int(user[2:-1].replace("!", ""))
    else:
        try:
            user_id = int(user)
        except ValueError:
            return (
                jsonify(
                    {
                        "error": "Invalid user input. Please provide 'me', a user ID, or mention a user."
                    }
                ),
                400,
            )

    if market == "all":
        market_id = None
    else:
        try:
            market_id = int(market)
        except ValueError:
            return (
                jsonify(
                    {
                        "error": "Invalid market input. Please provide a valid market ID or 'all'."
                    }
                ),
                400,
            )

    if market_id is not None:
        # Check if the market exists
        c.execute("SELECT id FROM markets WHERE id = ?", (market_id,))
        market = c.fetchone()
        if market is None:
            return (
                jsonify({"error": f"Market with ID {market_id} does not exist."}),
                404,
            )

    # Calculate PNL for the specified user(s) and market(s)
    if user_id is not None and market_id is not None:
        c.execute(
            """
            SELECT SUM(CASE WHEN t.buyer_id = ? THEN -t.price_cents * t.quantity ELSE t.price_cents * t.quantity END) / 100.0 AS pnl
            FROM trades t
            WHERE t.market_id = ? AND (t.buyer_id = ? OR t.seller_id = ?)
        """,
            (user_id, market_id, user_id, user_id),
        )
    elif user_id is not None:
        c.execute(
            """
            SELECT SUM(CASE WHEN t.buyer_id = ? THEN -t.price_cents * t.quantity ELSE t.price_cents * t.quantity END) / 100.0 AS pnl
            FROM trades t
            WHERE t.buyer_id = ? OR t.seller_id = ?
        """,
            (user_id, user_id, user_id),
        )
    else:
        c.execute(
            """
            SELECT u.id, SUM(CASE WHEN t.buyer_id = u.id THEN -t.price_cents * t.quantity ELSE t.price_cents * t.quantity END) / 100.0 AS pnl
            FROM trades t
            JOIN users u ON t.buyer_id = u.id OR t.seller_id = u.id
            GROUP BY u.id
        """
        )

    result = c.fetchall()
    conn.close()

    if len(result) == 0:
        return (
            jsonify(
                {"error": "No PNL data found for the specified user(s) and market(s)."}
            ),
            404,
        )
    else:
        if user_id is not None:
            pnl = result[0][0]
            return jsonify({"pnl": f"PNL for user {user}: ${pnl:.2f}"})
        else:
            pnl_data = []
            for row in result:
                pnl_data.append({"user_id": row[0], "pnl": f"${row[1]:.2f}"})
            return jsonify({"pnl_data": pnl_data})


@app.route("/resolve_market", methods=["POST"])
def resolve_market():
    data = request.get_json()
    market_id = data["market_id"]
    outcome = data["outcome"]
    payout_dollars = data["payout_dollars"]

    # Function logic goes here
    payout_cents = int(payout_dollars * 100)

    conn = sqlite3.connect("market.db")
    c = conn.cursor()

    # Check if the market exists and is not already resolved
    c.execute("SELECT id, resolved_at FROM markets WHERE id = ?", (market_id,))
    market = c.fetchone()

    if market is None:
        return jsonify({"error": f"Market with ID {market_id} does not exist."}), 404

    if market[1] is not None:
        return (
            jsonify(
                {"error": f"Market with ID {market_id} has already been resolved."}
            ),
            400,
        )

    # Update the market with the resolution details
    c.execute(
        "UPDATE markets SET outcome = ?, payout_cents = ?, resolved_at = CURRENT_TIMESTAMP WHERE id = ?",
        (outcome, payout_cents, market_id),
    )
    conn.commit()
    conn.close()

    return jsonify(
        {
            "message": f"Market with ID {market_id} has been resolved with outcome '{outcome}' and a payout of ${payout_dollars:.2f}."
        }
    )


def get_market_by_id_or_name(market_id=None, market_name=None):
    conn = sqlite3.connect("market.db")
    c = conn.cursor()

    if market_id is not None:
        c.execute("SELECT id, name FROM markets WHERE id = ?", (market_id,))
    elif market_name is not None:
        c.execute("SELECT id, name FROM markets WHERE name = ?", (market_name,))
    else:
        return None

    market = c.fetchone()
    conn.close()

    return market


def get_clob_data(market_id):
    conn = sqlite3.connect("market.db")
    c = conn.cursor()

    # Fetch buy orders for the market
    c.execute(
        """
        SELECT price_cents, SUM(quantity) as total_quantity
        FROM orders
        WHERE market_id = ? AND order_direction = 'buy' AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
        GROUP BY price_cents
        ORDER BY price_cents DESC
        """,
        (market_id,),
    )
    buy_orders = c.fetchall()

    # Fetch sell orders for the market
    c.execute(
        """
        SELECT price_cents, SUM(quantity) as total_quantity
        FROM orders
        WHERE market_id = ? AND order_direction = 'sell' AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
        GROUP BY price_cents
        ORDER BY price_cents ASC
        """,
        (market_id,),
    )
    sell_orders = c.fetchall()

    conn.close()

    return buy_orders, sell_orders


@app.route("/clob", methods=["GET"])
def get_clob():
    market_id = request.args.get("market_id")
    market_name = request.args.get("market_name")

    if market_id is not None:
        try:
            market_id = int(market_id)
        except ValueError:
            return (
                jsonify(
                    {"error": "Invalid market ID. Please provide a valid integer."}
                ),
                400,
            )
    elif market_name is None:
        return (
            jsonify({"error": "Please provide either a market ID or market name."}),
            400,
        )

    market = get_market_by_id_or_name(market_id, market_name)
    if market is None:
        return jsonify({"error": "Market not found."}), 404

    market_id, market_name = market
    buy_orders, sell_orders = get_clob_data(market_id)

    # Prepare the response data
    clob_data = {
        "market_id": market_id,
        "market_name": market_name,
        "buy_orders": [
            {"price_cents": order[0], "total_quantity": order[1]}
            for order in buy_orders
        ],
        "sell_orders": [
            {"price_cents": order[0], "total_quantity": order[1]}
            for order in sell_orders
        ],
    }

    return jsonify(clob_data)


if __name__ == "__main__":
    app.run()
