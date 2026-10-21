# herdr_stb/tracker.py
"""Turns a stream of agent snapshots into 'blocked' and 'done' events."""


class Tracker:
    def __init__(self, min_work=20.0, settle=2.0):
        self.min_work = min_work  # shorter turns are not worth a message
        self.settle = settle      # blocked must hold this long (filters flicker)
        self.panes = {}

    def update(self, agents, now):
        """Return [(kind, agent, seconds)] for kind in 'blocked', 'done'."""
        events = []
        live = set()
        for a in agents:
            pid, st = a["pane_id"], a["agent_status"]
            live.add(pid)
            if st == "unknown":
                continue
            s = self.panes.setdefault(pid, {"status": None, "since": now, "work": None, "sent": False})
            if st != s["status"]:
                if st == "working" and s["work"] is None:
                    s["work"] = now
                s["status"], s["since"], s["sent"] = st, now, False
            if st == "blocked" and not s["sent"] and now - s["since"] >= self.settle:
                s["sent"] = True
                events.append(("blocked", a, 0.0))
            elif st in ("idle", "done") and s["work"] is not None:
                dur, s["work"] = now - s["work"], None
                if dur >= self.min_work:
                    events.append(("done", a, dur))
        for pid in set(self.panes) - live:
            del self.panes[pid]
        return events
