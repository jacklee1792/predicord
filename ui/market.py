from typing import Optional

import flask
from flask import Blueprint

from db import Database
from db.objects import Market
from ui import require_login

bp = Blueprint("market", __name__, url_prefix="/market")


@bp.route("/<int:market_id>")
@require_login
def index(market_id):
    with flask.g.db as db:
        db: Database
        m: Optional[Market] = db.get_market_by_id(market_id)
        if not m:
            return "Market not found"
        o = db.get_orders_by_market_id(market_id)

    return flask.render_template("market/index.html", market=m, orders=o)


@bp.route("/create", methods=["GET", "POST"])
@require_login
def create():
    if flask.request.method == "GET":
        return flask.render_template("market/create.html")

    # POST; create new market
    name = flask.request.form.get("name")
    criteria = flask.request.form.get("criteria")
    user_id = flask.session.get("user_id")
    if not name or not criteria or not user_id:
        return "Failed to create new market"

    with flask.g.db as db:
        db.create_market(name=name, creator_id=user_id, criteria=criteria)

    return flask.redirect(flask.url_for("index"))


@bp.route("/update/<int:market_id>", methods=["GET", "POST"])
@require_login
def update(market_id):
    if flask.request.method == "GET":
        with flask.g.db as db:
            m: Optional[Market] = db.get_market_by_id(market_id)
            if not m:
                return "Market not found"
        return flask.render_template("market/update.html", market=m)

    # POST; update market
    name = flask.request.form.get("name")
    criteria = flask.request.form.get("criteria")
    if not market_id or not name or not criteria:
        return "Failed to update market"

    with flask.g.db as db:
        db.update_market(market_id, name, criteria)

    return flask.redirect(flask.url_for("index"))


@bp.route("/delete/<int:market_id>", methods=["POST"])
@require_login
def delete(market_id):
    with flask.g.db as db:
        db.delete_market(market_id)

    return flask.redirect(flask.url_for("index"))
