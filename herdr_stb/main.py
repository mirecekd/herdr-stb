# herdr_stb/main.py
"""Service loop and command line: run | on | off | status | test."""
import os
import sys
import threading
import time

from . import herdr, message, telegram
from .bot import Bot
from .tracker import Tracker

STATE_DIR = os.path.expanduser("~/.config/herdr-stb")
FLAG = os.path.join(STATE_DIR, "enabled")
ENV_FILE = os.environ.get("HERDR_STB_ENV") or os.path.expanduser("~/.config/herdr/telegram.env")
POLL = 2.0


def log(msg):
    print(msg, file=sys.stderr, flush=True)


def notify(bot, kind, agent, seconds):
    try:
        label = herdr.workspaces().get(agent["workspace_id"], "")
        if kind == "blocked":
            if bot.offer(agent, label):  # interactive message with buttons
                log("offered %s" % agent["pane_id"])
                return
            detail = message.dialog_text(herdr.screen(agent["pane_id"]))
        else:
            session = agent.get("agent_session") or {}
            since = time.time() - seconds
            detail = message.last_assistant_text(session["value"], since) if session.get("kind") == "path" else ""
        # shortcut: no retry if Telegram is down, add a queue when losing a message matters
        telegram.send(telegram.load_env(ENV_FILE), message.build(kind, agent, label, seconds, detail))
        log("sent %s %s" % (kind, agent["pane_id"]))
    except Exception as e:  # keep the service alive whatever one notification does
        log("notify failed (%s %s): %s" % (kind, agent["pane_id"], e))


def run():
    tracker = Tracker()
    bot = Bot(ENV_FILE, lambda: os.path.exists(FLAG))
    threading.Thread(target=bot.poll_forever, daemon=True).start()
    log("herdr-stb started, notifications %s" % ("on" if os.path.exists(FLAG) else "off"))
    while True:
        try:
            for kind, agent, seconds in tracker.update(herdr.agents(), time.time()):
                if os.path.exists(FLAG):  # tracked even when off, so switching on does not replay old events
                    notify(bot, kind, agent, seconds)
        except Exception as e:
            log("poll failed: %s" % e)
        bot.tick()
        time.sleep(POLL)


def main(argv):
    cmd = argv[0] if argv else "status"
    if cmd == "run":
        run()
    elif cmd == "on":
        os.makedirs(STATE_DIR, exist_ok=True)
        open(FLAG, "a").close()
        print("notifications on")
    elif cmd == "off":
        if os.path.exists(FLAG):
            os.remove(FLAG)
        print("notifications off")
    elif cmd == "status":
        print("notifications", "on" if os.path.exists(FLAG) else "off")
    elif cmd == "test":
        telegram.send(telegram.load_env(ENV_FILE), "herdr-stb: test message")
        print("sent")
    else:
        print("usage: herdr-stb run|on|off|status|test")
        return 2
    return 0
