import os
import urllib.parse

import flask
from flask import Flask
import requests

app = Flask(__name__)
app.secret_key = "your_secret_key"  # Change this to a secure random key
app.config['SESSION_TYPE'] = 'filesystem'

CLIENT_ID = os.getenv("DISCORD_CLIENT_ID")
CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET")
REDIRECT_URI = os.getenv("DISCORD_REDIRECT_URI")


# Routes
@app.route('/')
def index():
    if 'discord_user' in flask.session:
        return flask.redirect(flask.url_for('profile'))
    else:
        return '<a href="/login">Login with Discord</a>'


@app.route('/login')
def login():
    """
    Redirects the user to the Discord OAuth2 login page.
    """
    url = "https://discord.com/api/oauth2/authorize?"
    params = {
        'client_id': CLIENT_ID,
        'redirect_uri': REDIRECT_URI,
        'response_type': 'code',
        'scope': 'identify'
    }
    return flask.redirect(url + urllib.parse.urlencode(params))


@app.route('/callback')
def callback():
    """
    Handles the callback from Discord after the user has authorized.
    """
    code = flask.request.args.get('code')
    if not code:
        return 'Error: No authorization code provided.'

    # 1. Exchange the authorization code for an access token
    token_data = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': REDIRECT_URI,
        'scope': 'identify'
    }
    url = f"https://discord.com/api/oauth2/token"
    res = requests.post(url, data=token_data)
    if res.status_code != 200:
        return 'Failed to get access token.'
    res = res.json()
    url = "https://discord.com/api/oauth2/@me"
    headers = {'Authorization': f'Bearer {res["access_token"]}'}

    # 2. Use the access token to get the user's account information, write to
    # the user session
    res = requests.get(url, headers=headers)
    if res.status_code != 200:
        return 'Failed to get user info.'
    res = res.json()
    flask.session['discord_user'] = res
    return flask.redirect(flask.url_for('profile'))


@app.route('/profile')
def profile():
    user = flask.session.get('discord_user')
    if user:
        user = user["user"]
        name = user.get("global_name")
        return f"Logged in as {name}. <a href='/logout'>Logout</a>"
    else:
        return flask.redirect(flask.url_for('login'))


@app.route('/logout')
def logout():
    flask.session.pop('discord_user', None)
    return flask.redirect(flask.url_for('index'))


if __name__ == '__main__':
    app.run(debug=True)
