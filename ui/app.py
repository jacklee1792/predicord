import os
import sqlite3
import urllib.parse
from typing import List, Optional

import flask
from flask import Flask
import requests

from db import Database
from db.objects import Market

app = Flask(__name__, template_folder="templates")
app.secret_key = "todo: change this"
app.config["SESSION_TYPE"] = "filesystem"

CLIENT_ID = os.getenv("DISCORD_CLIENT_ID")
CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET")
REDIRECT_URI = os.getenv("DISCORD_REDIRECT_URI")


@app.before_request
def before_request():
    conn = sqlite3.connect("prediction_markets.db")
    flask.g.db = Database(conn)
    with flask.g.db as db:
        flask.g.markets = db.get_markets()


# Routes
@app.route("/")
def index():
    if "discord_user" in flask.session:
        return flask.redirect("/home")
    else:
        return '<a href="/login">Login with Discord</a>'


@app.route("/login")
def login():
    """
    Redirects the user to the Discord OAuth2 login page.
    """
    url = "https://discord.com/api/oauth2/authorize?"
    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": "identify",
    }
    return flask.redirect(url + urllib.parse.urlencode(params))


@app.route("/callback")
def callback():
    """
    Handles the callback from Discord after the user has authorized.
    """
    code = flask.request.args.get("code")
    if not code:
        return "Error: No authorization code provided."

    # 1. Exchange the authorization code for an access token
    token_data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "scope": "identify",
    }
    url = f"https://discord.com/api/oauth2/token"
    res = requests.post(url, data=token_data)
    if res.status_code != 200:
        return "Failed to get access token."
    res = res.json()
    url = "https://discord.com/api/oauth2/@me"
    headers = {"Authorization": f'Bearer {res["access_token"]}'}

    # 2. Use the access token to get the user's account information, write to
    # the user session
    res = requests.get(url, headers=headers)
    if res.status_code != 200:
        return "Failed to get user info."
    res = res.json()
    flask.session["discord_user"] = res["user"]
    return flask.redirect("/home")


@app.route("/home")
def home():
    user = flask.session.get("discord_user")
    if not user:
        return flask.redirect("/login")
    return flask.render_template("home.html", markets=flask.g.markets, user=user)


@app.route("/market/<int:market_id>")
def market(market_id):
    with flask.g.db as db:
        db: Database
        m: Optional[Market] = db.get_market_by_id(market_id)
        if not m:
            return "Market not found"

    return flask.render_template("market.html", market=m)


@app.route("/logout")
def logout():
    flask.session.pop("discord_user", None)
    return flask.redirect("/home")


@app.route("/submit/create_market", methods=["POST"])
def submit_create_market():
    name = flask.request.form.get("name")
    criteria = flask.request.form.get("criteria")
    user_id = flask.session["discord_user"].get("id")
    if not name or not criteria or not user_id:
        return "Failed to create new market"

    with flask.g.db as db:
        db: Database
        db.create_market(name=name, creator_id=user_id, criteria=criteria)
    return flask.redirect("/home")


if __name__ == "__main__":
    app.run(debug=True)
