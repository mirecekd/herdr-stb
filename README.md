# herdr-stb

Herdr simple Telegram bridge. A small systemd user service that watches every coding agent running in [Herdr](https://herdr.dev) and sends you a Telegram message in two cases only:

- an agent is waiting for your answer (blocked), with the question text; for pi with the ask-user tool you also get buttons, and your tap or reply goes straight back to the agent,
- an agent finished a longer piece of work (done), with its final message (pi) or a short header (other agents).

Everything else stays quiet. Notifications are off until you switch them on.

<div align="center">

[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://www.buymeacoffee.com/mirecekd) [!["PayPal.me"](https://www.paypalobjects.com/en_US/i/btn/btn_donateCC_LG.gif)](https://www.paypal.com/donate/?business=LJ5ZF7Q9KMTRW&no_recurring=0&currency_code=USD)

</div>

## Requirements

- Herdr 0.9 or newer with its pi integration (`herdr integration install pi`)
- Python 3, standard library only (developed on 3.14)
- Linux with `systemd --user`
- A Telegram bot token and your chat ID

## Setup

Create a bot with @BotFather, write one message to it, then put the values into `~/.config/herdr/telegram.env` (mode 600):

```
TELEGRAM_BOT_TOKEN=123456:ABC...
TELEGRAM_CHAT_ID=123456789
```

Read the chat ID from `https://api.telegram.org/bot<TOKEN>/getUpdates` (`message.chat.id`). Never paste the token into a shell command or a chat.

Install and start the service:

```
./install.sh
cp examples/herdr-stb-bridge.ts ~/.pi/agent/extensions/   # pi only, enables buttons and the blocked state
herdr-stb test      # sends a test message
herdr-stb on        # switch notifications on
```

## Telegram commands

| Command | Meaning |
|---|---|
| `/windows` | list every agent window as a button matrix; tap one to open a live view, then type to send text into it |
| `/new` | pick a project from `~/DEVEL` (the `ROOT` constant in `herdr_stb/projects.py`) (running ones first, or search by name), pick an agent, and start it in a new Herdr workspace; you are attached to it right away |
| `/on`, `/off` | turn notifications on or off |

The live view shows the last lines of the window and is edited about every 2 seconds. Buttons below it send Up, Down, Enter, Esc. Reading and typing use only generic Herdr calls, so it works with any agent Herdr recognizes. A pending question has priority over typing.

## Commands

| Command | Meaning |
|---|---|
| `herdr-stb on` / `off` | switch notifications on or off, takes effect immediately |
| `herdr-stb status` | show the switch |
| `herdr-stb test` | send a test message |
| `herdr-stb run` | the service loop (started by systemd) |

Logs: `journalctl --user -u herdr-stb -f`.

## How it works

The service subscribes to Herdr's event stream on its socket: one global subscription (pane created, agent detected, pane closed or exited) and one per pane with an agent (agent status changed). An event only wakes the main loop, which then reads a fresh `agent.list` snapshot, so a lost or duplicated event cannot corrupt state. A 30 second safety poll covers missed events, and subscriptions reconnect with back-off, which also covers a Herdr restart. New panes are subscribed on the next wake-up and closed ones are dropped.

A `blocked` state that holds for 2 seconds produces one message with the question and buttons. A turn that ran for 20 seconds or more and then returned to idle or done produces one message with the last assistant text from the pi session file. Events seen while notifications are off are discarded, so switching on never replays old ones.

## Restarting Herdr

The service is a separate systemd unit, so it keeps running while Herdr is down. It retries the connection with a growing delay, and when the socket is back it subscribes again by itself. No action is needed.

Herdr itself decides whether agents come back after a restart. To get them back into their own sessions, enable this in `~/.config/herdr/config.toml`:

```toml
[session]
resume_agents_on_restore = true
```

Restoring may be incomplete: a pane can come back as a plain shell, and workspace and pane ids can change. The service stores no ids, so it is not affected. A pi session that was not restored can be resumed with `pi --resume` in its folder.

An open `/windows` view is held in memory and is dropped when the service restarts.

## Formatting

Agent text is markdown. It is converted to the HTML subset Telegram supports (bold, headings as bold, inline code, code blocks, links; tables become aligned monospace blocks). If Telegram rejects a message's markup, it is resent as plain text.

## Known limits

- `/new` takes about 10 seconds because the agent has to start. It runs in the background, so the bot stays usable. A start that fails waits up to 45 seconds, then removes the empty workspace and says so.
- `/new` offers the agents found on the `PATH` of your interactive shell. The list of known agent kinds is fixed in `herdr_stb/projects.py` and follows `herdr agent --help`. Only `pi` was tested end to end; the others are started by Herdr's own `agent start`.
- Herdr marks a pane `blocked` only if the agent reports it. The buttons and the `blocked` state for pi need the bridge extension `examples/herdr-stb-bridge.ts` (copy it to `~/.pi/agent/extensions/`); it works with `@juicesharp/rpiv-ask-user-question`. Without it, pi panes that ask a question are not reported as blocked. Panes already running need a restart or `/reload` after you copy it.
- The final message is read only for pi sessions. Other agents get the header without text.
- A message lost while Telegram is unreachable is not retried.
- Free text answers a question when you reply to its message, or when exactly one question is open. With several open, reply to the one you mean.
- Questions asked by sub-agents that run on their own event bus (for example `/lanes` child runs) are not reachable.

## Tests

```
python3 -m unittest discover -s tests -t .
```

## Support

<div align="center">

[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://www.buymeacoffee.com/mirecekd) [!["PayPal.me"](https://www.paypalobjects.com/en_US/i/btn/btn_donateCC_LG.gif)](https://www.paypal.com/donate/?business=LJ5ZF7Q9KMTRW&no_recurring=0&currency_code=USD)

</div>

## License

MIT, see `LICENSE`.
