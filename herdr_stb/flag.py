# herdr_stb/flag.py
"""The on/off switch for notifications: a flag file shared by the CLI, the bot and the service."""
import os

STATE_DIR = os.path.expanduser("~/.config/herdr-stb")
FLAG = os.path.join(STATE_DIR, "enabled")


def is_on():
    return os.path.exists(FLAG)


def set_on(on):
    if on:
        os.makedirs(STATE_DIR, exist_ok=True)
        open(FLAG, "a").close()
    elif is_on():
        os.remove(FLAG)
