# herdr_stb/events.py
"""Wake-up signals from Herdr's event subscriptions.

Events carry no state we trust: they only say "look now". The main loop then reads a fresh
agent.list snapshot, so a missed or duplicated event can never corrupt the tracker.
"""
import json
import socket
import threading
import time

from . import herdr

GLOBAL = [{"type": t} for t in ("pane.created", "pane.agent_detected", "pane.closed", "pane.exited")]


class Events:
    def __init__(self, log):
        self.log = log
        self.wake = threading.Event()
        self.lock = threading.Lock()
        self.watchers = {}  # pane_id -> stop flag
        self.stopping = False

    def start(self):
        threading.Thread(target=self._listen, args=("global", GLOBAL, None), daemon=True).start()

    def sync(self, pane_ids):
        """Make the per-pane subscriptions match the given panes (subscribe new, drop closed)."""
        pane_ids = set(pane_ids)
        with self.lock:
            for pid in pane_ids - set(self.watchers):
                stop = threading.Event()
                self.watchers[pid] = stop
                subs = [{"type": "pane.agent_status_changed", "pane_id": pid}]
                threading.Thread(target=self._listen, args=(pid, subs, stop), daemon=True).start()
            for pid in set(self.watchers) - pane_ids:
                self.watchers.pop(pid).set()

    def _listen(self, name, subs, stop):
        """Hold one subscription. Reconnect with back-off until stopped; a reconnect also wakes the loop."""
        delay = 1
        while not self.stopping and not (stop and stop.is_set()):
            try:
                with socket.socket(socket.AF_UNIX) as s:
                    s.connect(herdr.sock_path())
                    s.settimeout(2)
                    s.sendall((json.dumps({"id": "sub", "method": "events.subscribe",
                                           "params": {"subscriptions": subs}}) + "\n").encode())
                    delay = 1
                    self.wake.set()  # anything that happened while we were not connected
                    while not self.stopping and not (stop and stop.is_set()):
                        try:
                            chunk = s.recv(65536)
                        except socket.timeout:
                            continue
                        if not chunk:
                            break
                        if b'"event"' in chunk:
                            self.wake.set()
            except OSError as e:
                if name == "global":
                    self.log("events: %s, retry in %ds" % (e, delay))
            if stop and stop.is_set():
                return
            time.sleep(delay)
            delay = min(delay * 2, 30)
