# herdr-stb

Herdr simple Telegram bridge. A small systemd user service that watches every coding agent running in [Herdr](https://herdr.dev) and sends you a Telegram message in two cases only:

- an agent is waiting for your answer (blocked): you get the question with buttons, tap an option or reply with your own text, and the answer goes straight back to pi,
- an agent finished a longer piece of work (done), with its final message.

Everything else stays quiet. Notifications are off until you switch them on.

<div align="center">

[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://www.buymeacoffee.com/mirecekd) [!["PayPal.me"](https://www.paypalobjects.com/en_US/i/btn/btn_donateCC_LG.gif)](https://www.paypal.com/donate/?business=LJ5ZF7Q9KMTRW&no_recurring=0&currency_code=USD)

</div>

## Requirements

- Herdr 0.9 or newer with its pi integration (`herdr integration install pi`)
- Python 3.9 or newer, no extra packages
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
herdr-stb test      # sends a test message
herdr-stb on        # switch notifications on
```

## Telegram commands

| Command | Meaning |
|---|---|
| `/windows` | list every agent window as a button matrix; tap one to open a live view, then type to send text into it |
| `/new` | pick a project from `~/DEVEL` (running ones first, or search by name), pick an agent, and start it in a new Herdr workspace; you are attached to it right away |
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

## Surviving a Herdr restart

Tested with a real `herdr server stop` and start, with six pi agents running:

- The service keeps running (it is a separate systemd unit). It logs a few `events: ... retry in 2s/4s/8s` lines while Herdr is down, reconnects by itself when the socket is back, and needs no restart or action.
- The event subscriptions are re-created automatically, because the service re-reads the agent list on every reconnect.
- With `resume_agents_on_restore = true` in the `[session]` section of `~/.config/herdr/config.toml`, Herdr restored 5 of 6 agents into their own pi sessions, with the same session files. The sixth pane came back as an empty shell (its session file is intact; resume it with `pi --resume` in that folder). The cause was not found in the Herdr logs.
- `pane_history = true` (section `[experimental]`) was set too. It is an experimental Herdr option.

An attached `/windows` view lives only in the service's memory, so it is dropped when the service restarts. Pending questions are written to `~/.config/herdr-stb/questions/` and removed when pi exits or the question is closed.

Suggested config:

```toml
[session]
resume_agents_on_restore = true

[experimental]
pane_history = true
```

## Formatting

Agent text is markdown. It is converted to the HTML subset Telegram supports (bold, headings as bold, inline code, code blocks, links; tables become aligned monospace blocks). If Telegram rejects a message's markup, it is resent as plain text.

## Known limits

- `/new` takes about 10 seconds because the agent has to start. It runs in the background, so the bot stays usable. A start that fails waits up to 45 seconds, then removes the empty workspace and says so.
- `/new` offers agents whose executable is on `PATH`, but only `pi` was tried end to end. Others are started by Herdr's own `agent start`.
- Herdr marks a pane `blocked` only if the agent reports it. For pi, the ask-user tool must emit `herdr:blocked`. With `@juicesharp/rpiv-ask-user-question` this needs a small bridge extension, see `examples/herdr-stb-bridge.ts` (copy it to `~/.pi/agent/extensions/`). The same file carries the questions to the service and the answers back.
- The final message is read only for pi sessions. Other agents get the header without text.
- A message lost while Telegram is unreachable is not retried.
- Free text is sent as an answer only through the "Type something" path of ask-user (a reply to the question message, or any message while exactly one question is open).
- Questions asked inside `/lanes` child runs are not reachable (they live on the child's own event bus).

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
