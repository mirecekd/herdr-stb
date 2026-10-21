# herdr_stb/ask.py
"""State of one ask-user questionnaire as seen from Telegram (pure logic, no I/O)."""
import hashlib

LABEL_MAX = 60


def key_of(tcid):
    return hashlib.sha1(tcid.encode()).hexdigest()[:8]  # callback_data is limited to 64 bytes


class Ask:
    def __init__(self, data, label):
        self.tcid = data["toolCallId"]
        self.key = key_of(self.tcid)
        self.fname = data["fname"]
        self.qs = data["questions"]
        self.label = label
        self.qi = 0
        self.answers = []
        self.sel = set()
        self.cancelled = False
        self.msg_id = None
        self.sent_at = None  # set once the answer is handed to pi

    @property
    def q(self):
        return self.qs[self.qi]

    def head(self):
        return "ASKS: %s  [%d/%d]" % (self.label, min(self.qi + 1, len(self.qs)), len(self.qs))

    def view(self):
        q = self.q
        lines = [self.head(), "", q["question"], ""]
        for i, o in enumerate(q["options"]):
            lines.append("%d. %s%s" % (i + 1, o["label"], " - " + o["description"] if o.get("description") else ""))
        lines += ["", "Tap an option or reply to this message with your own text."]
        rows = []
        for i, o in enumerate(q["options"]):
            mark = "[x] " if i in self.sel else ""
            rows.append([{"text": (mark + o["label"])[:LABEL_MAX], "callback_data": self._cb("o%d" % i)}])
        if q["multiSelect"]:
            rows.append([{"text": "Done", "callback_data": self._cb("d")}])
        rows.append([{"text": "Cancel", "callback_data": self._cb("c")}])
        return "\n".join(lines), rows

    def _cb(self, act):
        return "%s:%d:%s" % (self.key, self.qi, act)

    def press(self, data):
        """Handle a button. Returns (action, alert); action is edit, submit or ignore."""
        _, qi, act = data.split(":", 2)
        if int(qi) != self.qi:
            return "ignore", "That question is no longer active"
        if act == "c":
            self.cancelled = True
            return "submit", None
        if act == "d":
            if not self.sel:
                return "ignore", "Select at least one option"
            return self._answer(optionIndexes=sorted(self.sel))
        i = int(act[1:])
        if act[0] != "o" or not 0 <= i < len(self.q["options"]):
            return "ignore", "Unknown option"
        if self.q["multiSelect"]:
            self.sel ^= {i}
            return "edit", None
        return self._answer(optionIndexes=[i])

    def text(self, s):
        s = s.strip()
        if not s:
            return "ignore", None
        if self.q["multiSelect"] and self.sel:
            return self._answer(optionIndexes=sorted(self.sel), text=s)
        return self._answer(text=s)

    def _answer(self, **kw):
        self.answers.append(dict(questionIndex=self.qi, **kw))
        self.sel = set()
        self.qi += 1
        return ("submit", None) if self.qi >= len(self.qs) else ("edit", None)

    def payload(self):
        return {"cancel": True} if self.cancelled else {"answers": self.answers}

    def summary(self):
        if self.cancelled:
            return "Cancelled."
        out = []
        for a in self.answers:
            opts = self.qs[a["questionIndex"]]["options"]
            parts = [opts[i]["label"] for i in a.get("optionIndexes", [])]
            if a.get("text"):
                parts.append('"%s"' % a["text"])
            out.append("%s -> %s" % (self.qs[a["questionIndex"]]["question"], ", ".join(parts)))
        return "\n".join(out)
