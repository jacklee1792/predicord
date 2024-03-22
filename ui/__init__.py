import sqlite3

import flask
from flask import Flask

from db import Database
from ui.auth import require_login


def create_app(test_config=None):
    app = Flask(__name__, template_folder="templates")
    app.secret_key = "todo: change this"
    app.config["SESSION_TYPE"] = "filesystem"

    from . import auth
    from . import market
    from . import order

    app.register_blueprint(auth.bp)
    app.register_blueprint(market.bp)
    app.register_blueprint(order.bp)

    @app.before_request
    def before_request():
        if "user_id" in flask.session:
            conn = sqlite3.connect("prediction_markets.db")
            flask.g.db = Database(conn)

    @app.route("/")
    def index():
        if "user_id" in flask.session:
            with flask.g.db as db:
                flask.g.markets = db.get_markets()
        return flask.render_template("index.html")

    return app
