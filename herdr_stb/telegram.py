# herdr_stb/telegram.py
"""Tiny Telegram Bot API client and env-file reader (stdlib only)."""
import json
import urllib.error
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


def call(env, method, params, timeout=15):
    """Call a Bot API method. Errors never contain the URL, so the token cannot leak into logs."""
    req = urllib.request.Request(
        "https://api.telegram.org/bot%s/%s" % (env["TELEGRAM_BOT_TOKEN"], method),
        json.dumps(params).encode(), {"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.load(r)["result"]
    except urllib.error.HTTPError as e:
        raise RuntimeError("telegram %s: HTTP %s" % (method, e.code)) from None
    except urllib.error.URLError as e:
        raise RuntimeError("telegram %s unreachable: %s" % (method, e.reason)) from None


def send(env, text, rows=None):
    p = {"chat_id": env["TELEGRAM_CHAT_ID"], "text": text[:LIMIT]}
    if rows:
        p["reply_markup"] = {"inline_keyboard": rows}
    return call(env, "sendMessage", p)["message_id"]


def edit(env, message_id, text, rows=None):
    """Replace a message; without rows the keyboard is removed."""
    p = {"chat_id": env["TELEGRAM_CHAT_ID"], "message_id": message_id, "text": text[:LIMIT],
         "reply_markup": {"inline_keyboard": rows or []}}
    try:
        call(env, "editMessageText", p)
    except RuntimeError as e:
        if "HTTP 400" not in str(e):  # 400 also means "message is not modified", which is harmless
            raise
