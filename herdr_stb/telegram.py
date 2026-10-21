# herdr_stb/telegram.py
"""Tiny Telegram Bot API sender and env-file reader (stdlib only)."""
import json
import urllib.parse
import urllib.request

LIMIT = 3900  # Telegram hard limit is 4096 characters


def load_env(path):
    env = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip("'\"")
    return env


def send(env, text):
    """Send text to the configured chat. Raises on failure; never includes the token in errors."""
    data = urllib.parse.urlencode({"chat_id": env["TELEGRAM_CHAT_ID"], "text": text[:LIMIT]}).encode()
    url = "https://api.telegram.org/bot%s/sendMessage" % env["TELEGRAM_BOT_TOKEN"]
    try:
        with urllib.request.urlopen(url, data, timeout=15) as r:
            if not json.load(r).get("ok"):
                raise RuntimeError("telegram rejected the message")
    except urllib.error.HTTPError as e:
        raise RuntimeError("telegram HTTP %s" % e.code) from None
    except urllib.error.URLError as e:
        raise RuntimeError("telegram unreachable: %s" % e.reason) from None
