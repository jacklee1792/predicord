import functools
import os
import urllib.parse
from dataclasses import dataclass

import flask
import requests
from flask import Blueprint

from db.objects import User

bp = Blueprint("auth", __name__, url_prefix="/auth")


def require_login(f):
    """
    Redirect to login page if not already logged in
    """

    @functools.wraps(f)
    def wrapped_f(*args, **kwargs):
        if "user" not in flask.session:
            return flask.redirect(flask.url_for("auth.login"))
        return f(*args, **kwargs)

    return wrapped_f


@bp.route("/login")
def login():
    """
    Redirects the user to the Discord OAuth2 login page.
    """
    url = "https://discord.com/api/oauth2/authorize?"
    params = {
        "client_id": flask.current_app.config["DISCORD_CLIENT_ID"],
        "redirect_uri": flask.current_app.config["DISCORD_REDIRECT_URI"],
        "response_type": "code",
        "scope": "identify",
    }
    return flask.redirect(url + urllib.parse.urlencode(params))


@bp.route("/logout")
def logout():
    """
    Clears the session, effectively "logging out" the user.
    """
    flask.session.clear()
    return flask.redirect(flask.url_for("index"))


@bp.route("/callback")
def oauth_callback():
    """
    Handles the incoming callback from Discord after the user has authorized.
    """
    code = flask.request.args.get("code")
    if not code:
        return "Error: No authorization code provided."

    # 1. Exchange the authorization code for an access token
    token_data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": flask.current_app.config["DISCORD_REDIRECT_URI"],
        "scope": "identify",
    }
    url = f"https://discord.com/api/oauth2/token"
    auth = (
        flask.current_app.config["DISCORD_CLIENT_ID"],
        flask.current_app.config["DISCORD_CLIENT_SECRET"],
    )
    res = requests.post(url, data=token_data, auth=auth)
    if res.status_code != 200:
        return "Failed to get access token."

    # 2. Use the access token to get the user's account information, write to
    # the user session
    access_token = res.json()["access_token"]
    url = "https://discord.com/api/oauth2/@me"
    headers = {"Authorization": f"Bearer {access_token}"}
    res = requests.get(url, headers=headers)
    if res.status_code != 200:
        return "Failed to get user info."
    info = res.json()["user"]
    user_id, name, avatar_hash = info["id"], info["global_name"], info["avatar"]
    flask.session["user"] = User(id=user_id, display_name=name, avatar_hash=avatar_hash)
    with flask.g.db as db:
        db.upsert_user(discord_id=user_id, display_name=name, avatar_hash=avatar_hash)
    return flask.redirect(flask.url_for("index"))
