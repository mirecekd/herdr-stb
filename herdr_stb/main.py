# herdr_stb/main.py
"""Service loop and command line: run | on | off | status | test."""
import os
import sys
import threading
import time

from . import flag, herdr, message, telegram
from .bot import COMMANDS, Bot
from .events import Events
from .tracker import Tracker

ENV_FILE = os.environ.get("HERDR_STB_ENV") or os.path.expanduser("~/.config/herdr/telegram.env")
SAFETY_POLL = 30.0  # fallback when no event arrives
SETTLE_POLL = 1.0   # while a pane is blocked but not yet confirmed


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
    bot = Bot(ENV_FILE)
    try:
        telegram.set_commands(telegram.load_env(ENV_FILE), COMMANDS)
    except Exception as e:  # the menu is a convenience, the service works without it
        log("setMyCommands failed: %s" % e)
    threading.Thread(target=bot.poll_forever, daemon=True).start()
    events = Events(log)
    events.start()
    log("herdr-stb started, notifications %s" % ("on" if flag.is_on() else "off"))
    while True:
        try:
            snapshot = herdr.agents()
            events.sync(a["pane_id"] for a in snapshot)
            for kind, agent, seconds in tracker.update(snapshot, time.time()):
                if flag.is_on():  # tracked even when off, so switching on does not replay old events
                    notify(bot, kind, agent, seconds)
        except Exception as e:
            log("poll failed: %s" % e)
        bot.tick()
        # events wake us at once; the timeout is the safety net (missed events, new panes, Herdr restart)
        # and the tick for Tracker.settle, which needs a second look after a pane turns blocked
        events.wake.wait(SAFETY_POLL if not tracker.pending() else SETTLE_POLL)
        events.wake.clear()


def main(argv):
    cmd = argv[0] if argv else "status"
    if cmd == "run":
        run()
    elif cmd in ("on", "off"):
        flag.set_on(cmd == "on")
        print("notifications", cmd)
    elif cmd == "status":
        print("notifications", "on" if flag.is_on() else "off")
    elif cmd == "test":
        telegram.send(telegram.load_env(ENV_FILE), "herdr-stb: test message")
        print("sent")
    else:
        print("usage: herdr-stb run|on|off|status|test")
        return 2
    return 0
