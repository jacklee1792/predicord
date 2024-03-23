import time

import flask
from flask import Blueprint

from .auth import require_login

bp = Blueprint("order", __name__, url_prefix="/order")


@bp.route("/create", methods=["POST"])
@require_login
def create():
    order_type = flask.request.form.get("order_type")
    if order_type not in ("market", "limit"):
        return "Invalid order type"

    order_direction = flask.request.form.get("order_direction")
    if order_direction not in ("buy", "sell"):
        return "Invalid order direction"

    # Limit orders additionally require price/expiry
    # TODO change the name of this field "price_cents"
    if order_type == "limit":
        price_cents = round(float(flask.request.form["price_cents"]) * 1000)
        if not 0 < price_cents < 1000:
            return "Invalid price"
        expires_at = int(flask.request.form["expires_at"])
        if expires_at < time.time() * 1000:
            return "Invalid expiry"
    else:
        inf = 88888888
        price_cents = inf if order_direction == "buy" else 0
        expires_at = 0

    quantity = int(flask.request.form["quantity"])
    if quantity <= 0:
        return "Invalid quantity"

    with flask.g.db as db:
        db.create_order(
            market_id=int(flask.request.form["market_id"]),
            creator_id=flask.session["user"]["id"],
            order_type=order_type,
            order_direction=order_direction,
            price_cents=price_cents,
            quantity=quantity,
            expires_at=expires_at,
        )
    return flask.redirect(
        flask.url_for("market.index", market_id=flask.request.form["market_id"])
    )
