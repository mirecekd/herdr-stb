# herdr_stb/telegram.py
"""Tiny Telegram Bot API client and env-file reader (stdlib only)."""
import json
import urllib.error
import urllib.request

from .mdhtml import md_to_html

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


def _with_fallback(env, method, params, text):
    """Send formatted (HTML); if Telegram rejects the markup, resend the same text as plain."""
    text = text[:LIMIT]
    html_text = md_to_html(text)
    if len(html_text) <= 4096:
        try:
            return call(env, method, dict(params, text=html_text, parse_mode="HTML"))
        except RuntimeError as e:
            if "HTTP 400" not in str(e):
                raise
    return call(env, method, dict(params, text=text))


def send(env, text, rows=None):
    p = {"chat_id": env["TELEGRAM_CHAT_ID"]}
    if rows:
        p["reply_markup"] = {"inline_keyboard": rows}
    return _with_fallback(env, "sendMessage", p, text)["message_id"]


def edit(env, message_id, text, rows=None):
    """Replace a message; without rows the keyboard is removed."""
    p = {"chat_id": env["TELEGRAM_CHAT_ID"], "message_id": message_id,
         "reply_markup": {"inline_keyboard": rows or []}}
    try:
        _with_fallback(env, "editMessageText", p, text)
    except RuntimeError as e:
        if "HTTP 400" not in str(e):  # 400 here means "message is not modified", which is harmless
            raise


def delete(env, message_id):
    try:
        call(env, "deleteMessage", {"chat_id": env["TELEGRAM_CHAT_ID"], "message_id": message_id})
    except RuntimeError:
        pass  # already deleted or too old, nothing to clean up


def set_commands(env, commands):
    """Register the slash-command menu next to the text field."""
    call(env, "setMyCommands", {"commands": [{"command": c, "description": d} for c, d in commands]})
