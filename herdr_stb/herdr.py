# herdr_stb/herdr.py
"""Minimal Herdr socket API client (one request per connection)."""
import json
import os
import socket
import time


def sock_path():
    return os.environ.get("HERDR_SOCKET_PATH") or os.path.expanduser("~/.config/herdr/herdr.sock")


def rpc(method, params=None, timeout=10):
    with socket.socket(socket.AF_UNIX) as s:
        s.settimeout(timeout)
        s.connect(sock_path())
        s.sendall((json.dumps({"id": "stb", "method": method, "params": params or {}}) + "\n").encode())
        buf = b""
        while not buf.endswith(b"\n"):
            chunk = s.recv(65536)
            if not chunk:
                raise ConnectionError("herdr closed the socket")
            buf += chunk
    resp = json.loads(buf)
    if "error" in resp:
        raise RuntimeError(resp["error"].get("message", str(resp["error"])))
    return resp["result"]


def agents():
    return rpc("agent.list")["agents"]


def workspaces():
    return {w["workspace_id"]: w.get("label", "") for w in rpc("workspace.list")["workspaces"]}


def screen(pane_id):
    return rpc("pane.read", {"pane_id": pane_id, "source": "visible"})["read"]["text"]


def read(pane_id, lines=80):
    return rpc("pane.read", {"pane_id": pane_id, "source": "recent_unwrapped", "lines": lines})["read"]["text"]


def prompt(pane_id, text):
    """Type text into the agent in this pane and press Enter. Herdr refuses while the agent waits at a dialog."""
    rpc("agent.prompt", {"target": pane_id, "text": text})


def keys(pane_id, key_list):
    rpc("agent.send_keys", {"target": pane_id, "keys": list(key_list)})


def create_workspace(cwd, label):
    """New workspace in cwd; returns the id of its first pane."""
    r = rpc("workspace.create", {"cwd": cwd, "label": label, "focus": False})
    return r["workspace"]["workspace_id"], r["root_pane"]["pane_id"]


def start_agent(pane_id, name, kind, wait=15.0, ready=45.0):
    """Start an agent in a fresh pane and wait until it is ready for input.

    agent.start returns at once with the launch still pending, and a brand-new pane is
    not an 'available shell' for a moment, so retry on that and then poll for readiness.
    """
    end = time.time() + wait
    while True:
        try:
            rpc("agent.start", {"name": name, "kind": kind, "pane_id": pane_id, "timeout_ms": 30000}, timeout=40)
            break
        except RuntimeError as e:
            if "not an available shell" not in str(e) or time.time() > end:
                raise
            time.sleep(0.5)
    end = time.time() + ready
    while time.time() < end:
        a = next((x for x in agents() if x["pane_id"] == pane_id), None)
        if a and a.get("agent") and a["agent_status"] in ("idle", "working", "blocked", "done"):
            return
        time.sleep(1)
    raise RuntimeError("%s did not become ready in %d s" % (kind, ready))


def close_workspace(workspace_id):
    rpc("workspace.close", {"workspace_id": workspace_id})
