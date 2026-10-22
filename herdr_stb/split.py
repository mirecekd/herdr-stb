# herdr_stb/split.py
"""Split long text into pieces that fit a Telegram message after the HTML conversion."""
from .mdhtml import md_to_html

HTML_LIMIT = 4096
SAFE = 3500  # target length of the markdown source of one part; HTML escaping grows it, see fits()
MAX_PARTS = 8  # a runaway text must not flood the chat


def fits(text):
    return len(md_to_html(text)) <= HTML_LIMIT - 40  # room for the "(2/3)" marker


def _cut(text):
    """Largest prefix of text, cut at a paragraph, then a line, then a word, then anywhere."""
    window = text[:SAFE]
    for sep in ("\n\n", "\n", " "):
        i = window.rfind(sep)
        if i > SAFE // 3:
            return text[:i], text[i:].lstrip("\n ")
    return window, text[SAFE:]


def _balance(head, tail):
    """If a ``` fence is open at the cut, close it here and reopen it in the next part."""
    if head.count("```") % 2:
        return head + "\n```", "```\n" + tail
    return head, tail


def parts(text):
    """List of markdown pieces, each fitting one message. A runaway text loses its middle, never its end."""
    text = text.strip()
    out = []
    while text:
        if len(text) <= SAFE and fits(text):
            out.append(text)
            break
        head, tail = _cut(text)
        while not fits(head) and len(head) > 200:  # HTML escaping made it too long, shrink and retry
            head, tail = head[: int(len(head) * 0.8)], head[int(len(head) * 0.8):] + tail
        head, tail = _balance(head, tail)
        out.append(head)
        text = tail.strip()
    if len(out) > MAX_PARTS:
        # the ending usually holds the conclusion or the question, so drop from the middle, never the end
        keep_head, keep_tail = MAX_PARTS // 4 or 1, MAX_PARTS - MAX_PARTS // 4 - 1
        dropped = len(out) - keep_head - keep_tail
        out = out[:keep_head] + ["... %d parts left out, see the terminal ..." % dropped] + out[-keep_tail:]
    if len(out) > 1:
        out = ["%s\n\n(%d/%d)" % (p, i + 1, len(out)) for i, p in enumerate(out)]
    return out
