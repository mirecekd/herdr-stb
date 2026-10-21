# herdr_stb/message.py
"""Builds the text of a notification from an agent snapshot."""
import json
import os
import re

SEP = re.compile(r"^\s*[\u2500-\u257f\-=_]{20,}\s*$")
TAIL_BYTES = 400_000


def dialog_text(screen):
    """Extract the question dialog: the block between the last two separator lines."""
    parts, cur = [], []
    for line in screen.splitlines():
        if SEP.match(line):
            parts.append(cur)
            cur = []
        else:
            cur.append(line.rstrip())
    parts.append(cur)
    block = parts[-2] if len(parts) >= 3 else (parts[-1] if parts else [])
    lines = [x for x in block if x.strip()]
    if not lines:  # no recognisable dialog: fall back to the last lines of the screen
        lines = [x for x in screen.splitlines() if x.strip()][-12:]
    return "\n".join(lines)[:1500]


def last_assistant_text(session_path, since):
    """Last assistant text written at or after `since` (unix seconds), from a pi session JSONL."""
    try:
        with open(session_path, "rb") as f:
            f.seek(0, os.SEEK_END)
            f.seek(max(0, f.tell() - TAIL_BYTES))
            lines = f.read().decode("utf-8", "replace").splitlines()
    except OSError:
        return ""
    for line in reversed(lines):
        try:
            m = json.loads(line).get("message") or {}
        except ValueError:
            continue  # first line of the tail may be cut in half
        if m.get("role") != "assistant" or m.get("timestamp", 0) / 1000 < since - 5:
            continue
        text = "\n".join(c.get("text", "") for c in m.get("content", []) if c.get("type") == "text").strip()
        if text:
            return text[:1200]
    return ""


def build(kind, agent, label, seconds, detail):
    where = "%s / %s" % (label or agent["workspace_id"], os.path.basename(agent.get("cwd") or "") or "?")
    if kind == "blocked":
        head = "ASKS: %s (%s)" % (where, agent["pane_id"])
    else:
        head = "DONE: %s (%s, %d min %d s)" % (where, agent["pane_id"], seconds // 60, seconds % 60)
    return head + ("\n\n" + detail if detail else "")
