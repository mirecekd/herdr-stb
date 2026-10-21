# herdr_stb/windowbot.py
"""Telegram side of window browsing: /windows list, one live view of the attached window, typing into it."""
import time

from . import herdr, telegram, windows

REFRESH = 2.0       # minimum seconds between edits of the live message
IDLE_DETACH = 1800  # detach after this many seconds without interaction


class WindowBot:
    def __init__(self, env, log):
        self.env = env  # callable returning the current env dict
        self.log = log
        self.pane = None
        self.msg_id = None
        self.shown = None
        self.last_edit = 0.0
        self.last_touch = 0.0

    # ----- views -----
    def show_list(self):
        text, rows = windows.matrix(herdr.agents(), herdr.workspaces())
        telegram.send(self.env(), text, rows)

    def _agent(self):
        return next((a for a in herdr.agents() if a["pane_id"] == self.pane), None)

    def render(self, force=False):
        """Refresh the live message when the screen changed. Called from the service loop."""
        if not self.pane:
            return
        if time.time() - self.last_touch > IDLE_DETACH:
            self.detach("Detached after 30 minutes without activity.")
            return
        if not force and time.time() - self.last_edit < REFRESH:
            return
        a = self._agent()
        if a is None:
            self.detach("That window is gone.")
            return
        names = windows.labels(herdr.agents(), herdr.workspaces())
        text, rows = windows.live(names.get(self.pane, self.pane), a.get("agent"), a["agent_status"], herdr.read(self.pane))
        self.last_edit = time.time()
        if text == self.shown:
            return
        self.shown = text
        telegram.edit(self.env(), self.msg_id, text, rows)

    def attach(self, pane):
        self.detach()
        self.pane, self.shown, self.last_touch = pane, None, time.time()
        self.msg_id = telegram.send(self.env(), "Opening...")
        self.render(force=True)

    def detach(self, note="Detached."):
        if self.pane and self.msg_id:
            telegram.edit(self.env(), self.msg_id, *windows.back_to_list(note))
        self.pane = self.msg_id = self.shown = None

    # ----- input -----
    def press(self, data):
        """Handle a W: callback. Returns an alert text for the toast, or None."""
        _, act, *arg = data.split(":", 2)
        arg = arg[0] if arg else ""
        self.last_touch = time.time()
        if act == "l":
            self.show_list()
        elif act == "a":
            if not any(a["pane_id"] == arg for a in herdr.agents()):
                return "That window is gone"
            self.attach(arg)
        elif act == "d":
            self.detach()
        elif act == "k" and self.pane and arg in windows.KEYS:
            herdr.keys(self.pane, [arg])
            self.render(force=True)
        return None

    def text(self, s):
        """Type free text into the attached window. Returns a reply for the user, or None when sent."""
        if not self.pane:
            return "No window attached. Use /windows."
        a = self._agent()
        if a is None:
            self.detach("That window is gone.")
            return None
        if a["agent_status"] == "blocked":
            return "That window is waiting at a dialog. Use Up, Down, Enter, Esc below the view, or answer in the terminal."
        self.last_touch = time.time()
        herdr.prompt(self.pane, s)
        self.render(force=True)
        return None
