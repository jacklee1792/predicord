import functools
import os
import urllib.parse
from dataclasses import dataclass

import flask
import requests
from flask import Blueprint

bp = Blueprint("auth", __name__, url_prefix="/auth")


@dataclass
class OAuthParams:
    client_id: str
    client_secret: str
    redirect_uri: str


@functools.lru_cache(1)
def get_oauth_params():
    return OAuthParams(
        client_id=os.getenv("DISCORD_CLIENT_ID"),
        client_secret=os.getenv("DISCORD_CLIENT_SECRET"),
        redirect_uri=os.getenv("DISCORD_REDIRECT_URI"),
    )


def require_login(f):
    """
    Redirect to login page if not already logged in
    """

    @functools.wraps(f)
    def wrapped_f(*args, **kwargs):
        if "user_id" not in flask.session:
            return flask.redirect(flask.url_for("auth.login"))
        return f(*args, **kwargs)

    return wrapped_f


@bp.route("/login")
def login():
    """
    Redirects the user to the Discord OAuth2 login page.
    """
    url = "https://discord.com/api/oauth2/authorize?"
    oauth = get_oauth_params()
    params = {
        "client_id": oauth.client_id,
        "redirect_uri": oauth.redirect_uri,
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
    oauth = get_oauth_params()
    token_data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": oauth.redirect_uri,
        "scope": "identify",
    }
    url = f"https://discord.com/api/oauth2/token"
    res = requests.post(
        url, data=token_data, auth=(oauth.client_id, oauth.client_secret)
    )
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
    flask.session["user_id"] = res.json()["user"]["id"]
    return flask.redirect(flask.url_for("index"))
