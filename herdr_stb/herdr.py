# herdr_stb/herdr.py
"""Minimal Herdr socket API client (one request per connection)."""
import json
import os
import socket


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
