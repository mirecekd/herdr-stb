# herdr_stb/windows.py
"""Pure helpers: window labels, the /windows matrix and the live view text."""
import os

BTN_MAX = 60
LINES = 35   # screen lines in the live view
CHARS = 3300  # leaves room for the header inside Telegram's 4096 limit
KEYS = ("up", "down", "enter", "esc")


def labels(agents, workspaces):
    """Short unique name per pane: workspace label, plus folder or pane id when that is ambiguous."""
    per_ws = {}
    for a in agents:
        per_ws[a["workspace_id"]] = per_ws.get(a["workspace_id"], 0) + 1
    names = {}
    for a in agents:
        ws = workspaces.get(a["workspace_id"]) or a["workspace_id"]
        folder = os.path.basename(a.get("cwd") or "")
        names[a["pane_id"]] = ws if per_ws[a["workspace_id"]] == 1 else "%s/%s" % (ws, folder or a["pane_id"])
    seen = {}
    for n in names.values():
        seen[n] = seen.get(n, 0) + 1
    return {p: n if seen[n] == 1 else "%s %s" % (n, p) for p, n in names.items()}


def matrix(agents, workspaces):
    """(text, keyboard rows) listing every agent window, two buttons per row."""
    if not agents:
        return "No agents are running in Herdr.", []
    names = labels(agents, workspaces)
    btns = [{"text": ("%s (%s) - %s" % (names[a["pane_id"]], a.get("agent") or "?", a["agent_status"]))[:BTN_MAX],
             "callback_data": "W:a:" + a["pane_id"]} for a in agents]
    rows = [btns[i:i + 2] for i in range(0, len(btns), 2)]
    return "Herdr windows: %d. Tap one to open it." % len(agents), rows


def tail(screen):
    """Last lines of a screen: no trailing blanks, runs of blank lines collapsed, fits the live view."""
    out = []
    for line in screen.splitlines():
        line = line.rstrip()
        if line or (out and out[-1]):
            out.append(line)
    while out and not out[-1]:
        out.pop()
    body = "\n".join(out[-LINES:])
    return body[-CHARS:].replace("```", "'''") or "(empty)"


def live(label, kind, status, screen):
    """(text, rows) for the one live message of the attached window."""
    text = "%s (%s) - %s\n\n```\n%s\n```" % (label, kind or "?", status, tail(screen))
    rows = [[{"text": k.capitalize(), "callback_data": "W:k:" + k} for k in KEYS],
            [{"text": "Windows", "callback_data": "W:l"}, {"text": "Detach", "callback_data": "W:d"}]]
    return text, rows


def back_to_list(text):
    return text, [[{"text": "Windows", "callback_data": "W:l"}]]
