# herdr_stb/projects.py
"""Pure logic for /new: project list, search and the button screens."""
import os
import shutil
import subprocess
import time

ROOT = os.path.expanduser("~/DEVEL")
KINDS = ("pi", "claude", "codex", "gemini", "cursor", "opencode", "copilot", "kimi", "droid", "amp", "grok",
         "hermes", "kilo", "qwen", "letta", "devin", "cline", "kiro")  # as listed by `herdr agent --help`
RECENT = 8
SEARCH_MAX = 12
CACHE_SECONDS = 300
_cache = [0.0, []]


def installed_kinds():
    """Agent kinds found on the PATH of the user's interactive shell.

    The service runs under systemd with a bare PATH (no nvm, no ~/.local/bin), but Herdr starts the
    agent in the user's shell. Ask that shell, and cache the answer: an interactive shell takes ~0.5 s.
    """
    if time.time() - _cache[0] < CACHE_SECONDS and _cache[1]:
        return list(_cache[1])
    found = []
    try:
        shell = os.environ.get("SHELL") or "/bin/bash"
        out = subprocess.run([shell, "-ic", "for k in %s; do command -v \"$k\" >/dev/null 2>&1 && echo \"$k\"; done" % " ".join(KINDS)],
                             capture_output=True, text=True, timeout=15, stdin=subprocess.DEVNULL).stdout
        found = [k for k in out.split() if k in KINDS]
    except (OSError, subprocess.SubprocessError):
        pass
    found = found or [k for k in KINDS if shutil.which(k)]  # shortcut: the service PATH only, when the shell cannot be asked
    _cache[0], _cache[1] = time.time(), found
    return list(found)


def scan(root=ROOT):
    """[(name, is_git)] for the immediate subfolders of root, newest change first."""
    out = []
    try:
        for e in os.scandir(root):
            if e.is_dir(follow_symlinks=False) and not e.name.startswith("."):
                out.append((e.stat().st_mtime, e.name, os.path.isdir(os.path.join(e.path, ".git"))))
    except OSError:
        return []
    return [(n, g) for _, n, g in sorted(out, reverse=True)]


def recent(projects, active):
    """Folders with a running window first, then git repos by recent change."""
    live = [p for p in projects if p[0] in active]
    rest = [p for p in projects if p[0] not in active and p[1]]
    return (live + rest)[:RECENT]


def search(projects, query):
    q = query.strip().lower()
    if not q:
        return []
    hits = [p for p in projects if q in p[0].lower()]
    hits.sort(key=lambda p: (not p[0].lower().startswith(q), not p[1], len(p[0])))
    return hits[:SEARCH_MAX]


def _btn(text, data):
    return {"text": text[:60], "callback_data": data}


def home(projects, active):
    rows = [[_btn(n, "N:p:" + n)] for n, _ in recent(projects, active)]
    rows.append([_btn("Search...", "N:s"), _btn("Cancel", "N:x")])
    return "New window: pick a project (running ones first), or search.", rows


def results(hits, query):
    if not hits:
        return 'Nothing matches "%s". Send another search text.' % query, [[_btn("Cancel", "N:x")]]
    rows = [[_btn(n, "N:p:" + n)] for n, _ in hits]
    rows.append([_btn("Cancel", "N:x")])
    return 'Matches for "%s". Tap a project, or send another search text.' % query, rows


def kind_screen(project, kinds, last):
    ordered = sorted(kinds, key=lambda k: k != last)
    rows = [[_btn(k + (" (last used)" if k == last else ""), "N:k:" + k)] for k in ordered]
    rows.append([_btn("Back", "N:b"), _btn("Cancel", "N:x")])
    return "Project: %s\nWhich agent should start there?" % project, rows


def safe_name(name):
    """A project name coming from a button must be a plain folder name, never a path."""
    return bool(name) and name == os.path.basename(name) and name not in (".", "..")
