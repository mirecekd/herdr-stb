# herdr_stb/commands.py
"""Slash commands of the bot: the menu next to the text field and the handlers behind it."""
from . import flag, telegram

COMMANDS = [("windows", "List Herdr windows and open one"), ("new", "Start an agent in a new window"),
            ("on", "Turn notifications on"), ("off", "Turn notifications off")]
HELP = ("/windows - list Herdr windows, tap one to see it live and type into it\n"
        "/new - pick a project and an agent and start it in a new Herdr window\n"
        "/on, /off - turn notifications on or off\n\n"
        "A pending question has priority: tap its buttons or reply to its message.")


def parse(text):
    """Command name of a message like '/windows@mybot extra', or '' when it is not a command."""
    return text.split()[0].lstrip("/").split("@")[0].lower() if text.startswith("/") else ""


def handle(env, cmd, win, new):
    """Run a reserved command. False for anything else, which then goes on as ordinary typing."""
    if cmd == "windows":
        win.show_list()
    elif cmd == "new":
        new.begin()
    elif cmd in ("on", "off"):
        flag.set_on(cmd == "on")
        telegram.send(env, "Notifications %s." % cmd)
    elif cmd in ("start", "help"):
        telegram.send(env, HELP)
    else:
        return False
    return True
