from datetime import datetime

import humanize


def discord_avatar_url(user_id: str, avatar_hash: str) -> str:
    base_url = "https://cdn.discordapp.com/avatars/"
    if avatar_hash.startswith("a_"):
        return f"{base_url}{user_id}/{avatar_hash}.gif"
    return f"{base_url}{user_id}/{avatar_hash}.png"


def timedelta_from(timestamp: int) -> str:
    """
    Convert a timestamp (milliseconds since Unix epoch) into a human-readable
    relative time string.
    """
    delta = datetime.now() - datetime.fromtimestamp(timestamp / 1000)
    return humanize.naturaltime(delta)


def fmt_price(price_cents: int) -> str:
    return f"{price_cents / 1000:.3f}"
