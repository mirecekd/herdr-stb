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

## Commands

| Command | Meaning |
|---|---|
| `herdr-stb on` / `off` | switch notifications on or off, takes effect immediately |
| `herdr-stb status` | show the switch |
| `herdr-stb test` | send a test message |
| `herdr-stb run` | the service loop (started by systemd) |

Logs: `journalctl --user -u herdr-stb -f`.

## How it works

The service polls `agent.list` on the Herdr socket every 2 seconds. A `blocked` state that holds for 2 seconds produces one message with the dialog read from the pane. A turn that ran for 20 seconds or more and then returned to idle or done produces one message with the last assistant text from the pi session file. Events seen while notifications are off are discarded, so switching on never replays old ones.

## Formatting

Agent text is markdown. It is converted to the HTML subset Telegram supports (bold, headings as bold, inline code, code blocks, links). If Telegram rejects a message's markup, it is resent as plain text.

## Known limits

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
