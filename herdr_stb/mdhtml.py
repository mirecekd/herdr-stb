# herdr_stb/mdhtml.py
"""Convert the markdown agents write into the small HTML subset Telegram accepts."""
import html
import re


def md_to_html(text):
    keep = []

    def stash(s):
        keep.append(s)
        return "\x00%d\x00" % (len(keep) - 1)

    # code first: nothing inside it may be touched by the rules below
    text = re.sub(r"```[^\n]*\n?(.*?)```", lambda m: stash("<pre>%s</pre>" % html.escape(m.group(1).strip("\n"), quote=False)), text, flags=re.S)
    text = re.sub(r"`([^`\n]+)`", lambda m: stash("<code>%s</code>" % html.escape(m.group(1), quote=False)), text)
    text = html.escape(text, quote=False)
    text = re.sub(r"^#{1,6}\s+(.+)$", lambda m: "<b>%s</b>" % m.group(1).replace("**", ""), text, flags=re.M)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"\[([^\]\n]+)\]\((https?://[^)\s]+)\)",
                  lambda m: '<a href="%s">%s</a>' % (m.group(2).replace('"', "%22"), m.group(1)), text)
    return re.sub(r"\x00(\d+)\x00", lambda m: keep[int(m.group(1))], text)
