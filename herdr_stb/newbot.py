# herdr_stb/newbot.py
"""Telegram side of /new: pick a project, pick an agent, start it in a fresh Herdr workspace."""
import os
import re
import threading

from . import herdr, projects, telegram

STATE_DIR = os.path.expanduser("~/.config/herdr-stb")
LAST = os.path.join(STATE_DIR, "last_kind")
TIMEOUT = 600  # forget a half-finished /new after 10 minutes


def last_kind():
    try:
        with open(LAST, encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return ""


def remember_kind(kind):
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(LAST, "w", encoding="utf-8") as f:
        f.write(kind)


class NewBot:
    def __init__(self, env, log, attach, now):
        self.env, self.log, self.attach, self.now = env, log, attach, now
        self.msg_id = None
        self.project = None
        self.mode = None  # None | "search"
        self.started = 0.0

    def active(self):
        return self.msg_id is not None and self.now() - self.started < TIMEOUT

    def _show(self, text, rows):
        env = self.env()
        if self.msg_id is None:
            self.msg_id = telegram.send(env, text, rows)
        else:
            telegram.edit(env, self.msg_id, text, rows)

    def _running(self):
        return {os.path.basename(a.get("cwd") or "") for a in herdr.agents()}

    def begin(self):
        self.msg_id, self.project, self.mode, self.started = None, None, None, self.now()
        self._show(*projects.home(projects.scan(), self._running()))

    def _close(self, note):
        if self.msg_id is not None:
            telegram.edit(self.env(), self.msg_id, note)
        self.msg_id = self.project = self.mode = None

    def press(self, data):
        """Handle an N: callback. Returns a toast text or None."""
        if not self.active() and data != "N:x":
            return "This menu expired. Send /new again."
        _, act, *rest = data.split(":", 2)
        arg = rest[0] if rest else ""
        if act == "x":
            self._close("Cancelled.")
        elif act == "s":
            self.mode = "search"
            telegram.edit(self.env(), self.msg_id, "Send part of the project name.", [[{"text": "Cancel", "callback_data": "N:x"}]])
        elif act == "b":
            self.project, self.mode = None, None
            self._show(*projects.home(projects.scan(), self._running()))
        elif act == "p":
            if not projects.safe_name(arg) or not os.path.isdir(os.path.join(projects.ROOT, arg)):
                return "Unknown project"
            self.project, self.mode = arg, None
            kinds = projects.installed_kinds()
            if not kinds:
                self._close("No supported agent is installed.")
            else:
                self._show(*projects.kind_screen(arg, kinds, last_kind()))
        elif act == "k":
            return self.launch(arg)
        return None

    def text(self, s):
        """Search text. Returns True when it was consumed by /new."""
        if not (self.active() and self.mode == "search"):
            return False
        q = s.strip()
        self._show(*projects.results(projects.search(projects.scan(), q), q))
        return True

    def launch(self, kind):
        """Validate, then start in a background thread so the Telegram loop keeps serving (start takes 10 to 45 s)."""
        if not self.project or kind not in projects.installed_kinds():
            return "Pick a project first" if not self.project else "That agent is not installed"
        project, path = self.project, os.path.join(projects.ROOT, self.project)
        self._show("Starting %s in %s..." % (kind, project), [])
        self.msg_id, mid = None, self.msg_id  # a new /new may begin while this one is starting
        self.project = self.mode = None
        threading.Thread(target=self._start, args=(kind, project, path, mid), daemon=True).start()
        return None

    def _start(self, kind, project, path, mid):
        ws = pane = None
        try:
            ws, pane = herdr.create_workspace(path, project)
            name = re.sub(r"[^a-z0-9_-]", "-", project.lower())[:18].strip("-_") or "agent"
            # agent names must be unique among live agents and start with a letter
            herdr.start_agent(pane, "tg-%s-%s" % (name, ws.lower()), kind)
        except Exception as e:
            self.log("new failed: %s" % e)
            if ws:  # do not leave an empty workspace behind
                try:
                    herdr.close_workspace(ws)
                except Exception as e2:
                    self.log("cleanup failed: %s" % e2)
            telegram.edit(self.env(), mid, "Could not start %s in %s: %s" % (kind, project, str(e)[:200]))
            return
        remember_kind(kind)
        telegram.edit(self.env(), mid, "Started %s in %s." % (kind, project))
        self.attach(pane)
