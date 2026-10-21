# herdr_stb/bot.py
"""Interactive questions: offer them in Telegram, take the answer back to pi."""
import glob
import json
import os
import sys
import threading
import time

from . import telegram
from .ask import Ask

STATE_DIR = os.path.expanduser("~/.config/herdr-stb")
QDIR = os.path.join(STATE_DIR, "questions")
ADIR = os.path.join(STATE_DIR, "answers")
ACCEPT_WAIT = 8  # seconds pi gets to pick up an answer before we call it refused


def log(msg):
    print(msg, file=sys.stderr, flush=True)


class Bot:
    def __init__(self, env_file, enabled=lambda: True):
        self.env_file = env_file
        self.enabled = enabled
        self.lock = threading.RLock()
        self.pending = {}
        self.offset = None

    def env(self):
        return telegram.load_env(self.env_file)

    def find_question(self, pane):
        """Newest question file of a live pi process in this pane."""
        best = None
        for f in glob.glob(os.path.join(QDIR, "*.json")):
            try:
                with open(f, encoding="utf-8") as fh:
                    d = json.load(fh)
                os.kill(d["pid"], 0)  # a crashed pi leaves its file behind
                if d.get("pane") == pane and (best is None or os.path.getmtime(f) > best[0]):
                    best = (os.path.getmtime(f), f, d)
            except (OSError, ValueError, KeyError):
                continue
        return best

    def offer(self, agent, label):
        """Send the interactive version of a blocked pane. False when no question data exists."""
        found = self.find_question(agent["pane_id"])
        if not found:
            return False
        data = dict(found[2], fname=os.path.basename(found[1]))
        with self.lock:
            if any(a.fname == data["fname"] for a in self.pending.values()):
                return True
            ask = Ask(data, "%s / %s" % (label or agent["workspace_id"], os.path.basename(agent.get("cwd") or "?")))
            ask.msg_id = telegram.send(self.env(), *ask.view())
            self.pending[ask.key] = ask
        return True

    def submit(self, a):
        os.makedirs(ADIR, exist_ok=True)
        path = os.path.join(ADIR, a.fname)
        with open(path + ".tmp", "w", encoding="utf-8") as f:
            json.dump(a.payload(), f)
        os.replace(path + ".tmp", path)  # pi must never see a half-written file
        a.sent_at = time.time()
        telegram.edit(self.env(), a.msg_id, a.head() + "\n\nSending...")

    def finish(self, a, note):
        self.pending.pop(a.key, None)
        try:
            telegram.edit(self.env(), a.msg_id, a.head() + "\n\n" + note)
        except Exception as e:
            log("finish failed: %s" % e)

    def apply(self, a, action):
        if action == "edit":
            telegram.edit(self.env(), a.msg_id, *a.view())
        elif action == "submit":
            self.submit(a)

    def tick(self):
        with self.lock:
            for a in list(self.pending.values()):
                alive = os.path.exists(os.path.join(QDIR, a.fname))
                if a.sent_at is None and not alive:
                    self.finish(a, "Answered in the terminal.")
                elif a.sent_at is not None and not alive:
                    self.finish(a, "Answered from Telegram.\n" + a.summary())
                elif a.sent_at is not None and time.time() - a.sent_at > ACCEPT_WAIT:
                    self.finish(a, "pi did not accept the answer. Answer in the terminal.")

    def on_update(self, u):
        env = self.env()
        chat = str(env["TELEGRAM_CHAT_ID"])
        cb, msg = u.get("callback_query"), u.get("message")
        with self.lock:
            if cb and str((cb.get("message") or {}).get("chat", {}).get("id")) == chat:
                self.on_press(env, cb)
            elif msg and str(msg["chat"]["id"]) == chat and msg.get("text"):
                self.on_text(env, msg)

    def on_press(self, env, cb):
        data = cb.get("data", "")
        a = self.pending.get(data.split(":")[0])
        action, alert = "ignore", "Expired"
        if a and a.sent_at is None:
            try:
                action, alert = a.press(data)
            except (ValueError, IndexError):
                action, alert = "ignore", "Bad button"
        try:
            telegram.call(env, "answerCallbackQuery", {"callback_query_id": cb["id"], "text": alert or ""})
        except RuntimeError as e:
            log("answerCallbackQuery: %s" % e)
        if a and action != "ignore":
            self.apply(a, action)

    def on_text(self, env, msg):
        open_asks = [a for a in self.pending.values() if a.sent_at is None]
        reply = (msg.get("reply_to_message") or {}).get("message_id")
        a = next((x for x in open_asks if x.msg_id == reply), None) or (open_asks[0] if len(open_asks) == 1 else None)
        if a is None:
            telegram.send(env, "Several questions are open, reply to the one you mean." if open_asks
                          else "No open question to answer.")
            return
        action, _ = a.text(msg["text"])
        self.apply(a, action)

    def poll_forever(self):
        while True:
            try:
                env = self.env()
                if self.offset is None:  # skip anything sent while we were not running
                    ups = telegram.call(env, "getUpdates", {"offset": -1, "timeout": 0})
                    self.offset = ups[-1]["update_id"] + 1 if ups else 0
                params = {"offset": self.offset, "timeout": 25, "allowed_updates": ["message", "callback_query"]}
                for u in telegram.call(env, "getUpdates", params, timeout=40):
                    self.offset = u["update_id"] + 1
                    try:
                        if self.enabled():
                            self.on_update(u)
                    except Exception as e:
                        log("update failed: %s" % e)
            except Exception as e:
                log("poll failed: %s" % e)
                time.sleep(5)
