# herdr_stb/mdhtml.py
"""Convert the markdown agents write into the small HTML subset Telegram accepts."""
import html
import re

SEP_ROW = re.compile(r"^\s*\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)*\|?\s*$")


def _cells(line):
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    return [re.sub(r"\*\*|`", "", c).strip() for c in line.split("|")]


def _render_table(lines):
    """Aligned monospace text; Telegram has no table element, so this is the closest readable form."""
    head, rows = _cells(lines[0]), [_cells(x) for x in lines[2:]]
    width = max([len(head)] + [len(r) for r in rows])
    grid = [r + [""] * (width - len(r)) for r in [head] + rows]
    w = [max(len(r[i]) for r in grid) for i in range(width)]
    fmt = lambda r: "  ".join(c.ljust(w[i]) for i, c in enumerate(r)).rstrip()
    return "\n".join([fmt(grid[0]), "  ".join("-" * n for n in w)] + [fmt(r) for r in grid[1:]])


def _tables(text, stash):
    """Replace markdown tables (header row, separator row, body rows) with stashed <pre> blocks."""
    out, lines, i = [], text.split("\n"), 0
    while i < len(lines):
        if "|" in lines[i] and i + 1 < len(lines) and "|" in lines[i + 1] and SEP_ROW.match(lines[i + 1]):
            j = i + 2
            while j < len(lines) and "|" in lines[j] and lines[j].strip():
                j += 1
            out.append(stash("<pre>%s</pre>" % html.escape(_render_table(lines[i:j]), quote=False)))
            i = j
        else:
            out.append(lines[i])
            i += 1
    return "\n".join(out)


def md_to_html(text):
    keep = []

    def stash(s):
        keep.append(s)
        return "\x00%d\x00" % (len(keep) - 1)

    # code first: nothing inside it may be touched by the rules below
    text = re.sub(r"```[^\n]*\n?(.*?)```", lambda m: stash("<pre>%s</pre>" % html.escape(m.group(1).strip("\n"), quote=False)), text, flags=re.S)
    text = _tables(text, stash)
    text = re.sub(r"`([^`\n]+)`", lambda m: stash("<code>%s</code>" % html.escape(m.group(1), quote=False)), text)
    text = html.escape(text, quote=False)
    text = re.sub(r"^#{1,6}\s+(.+)$", lambda m: "<b>%s</b>" % m.group(1).replace("**", ""), text, flags=re.M)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"\[([^\]\n]+)\]\((https?://[^)\s]+)\)",
                  lambda m: '<a href="%s">%s</a>' % (m.group(2).replace('"', "%22"), m.group(1)), text)
    return re.sub(r"\x00(\d+)\x00", lambda m: keep[int(m.group(1))], text)
