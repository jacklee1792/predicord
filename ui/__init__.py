import os
import sqlite3

import flask
from flask import Flask
from git import Repo

from db import Database
from ui.auth import require_login


def create_app(test_config=None):
    app = Flask(__name__, template_folder="templates")
    app.secret_key = "todo: change this"

    # Blueprints
    from . import auth
    from . import market
    from . import order

    app.register_blueprint(auth.bp)
    app.register_blueprint(market.bp)
    app.register_blueprint(order.bp)

    # Jinja templating functions
    from . import jinja

    app.jinja_env.globals.update(discord_avatar_url=jinja.discord_avatar_url)
    app.jinja_env.globals.update(timedelta_from=jinja.timedelta_from)

    # App config
    app.config["SESSION_TYPE"] = "filesystem"
    client_id = os.getenv("DISCORD_CLIENT_ID")
    client_secret = os.getenv("DISCORD_CLIENT_SECRET")
    redirect_uri = os.getenv("DISCORD_REDIRECT_URI")
    for var in "DISCORD_CLIENT_ID", "DISCORD_CLIENT_SECRET", "DISCORD_REDIRECT_URI":
        val = os.getenv(var)
        assert val is not None, f"Missing environment variable: {var}"
        app.config[var] = val

    repo = Repo(search_parent_directories=True)
    branch = repo.active_branch.name
    sha = "dev" if repo.is_dirty() else repo.head.object.hexsha[:8]
    app.config["GIT_SHA"] = f"{branch}@{sha}"

    # Pre-request: establish database connection
    @app.before_request
    def before_request():
        conn = sqlite3.connect("prediction_markets.db")
        flask.g.db = Database(conn)

    @app.route("/")
    def index():
        if "user" in flask.session:
            with flask.g.db as db:
                flask.g.markets = db.get_markets()
        return flask.render_template("index.html")

    return app
