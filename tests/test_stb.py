# tests/test_stb.py
import json
import os
import tempfile
import unittest

from herdr_stb import message
from herdr_stb.tracker import Tracker


def ag(status, pane="w1:p1"):
    return {"pane_id": pane, "agent_status": status, "workspace_id": "w1", "cwd": "/x/proj"}


class TrackerTest(unittest.TestCase):
    def test_long_turn_gives_done(self):
        t = Tracker(min_work=20, settle=2)
        self.assertEqual(t.update([ag("idle")], 0), [])
        self.assertEqual(t.update([ag("working")], 10), [])
        ev = t.update([ag("done")], 70)
        self.assertEqual([(e[0], round(e[2])) for e in ev], [("done", 60)])
        self.assertEqual(t.update([ag("idle")], 80), [])  # reported once

    def test_short_turn_is_silent(self):
        t = Tracker(min_work=20)
        t.update([ag("working")], 0)
        self.assertEqual(t.update([ag("idle")], 5), [])

    def test_blocked_needs_to_settle_and_fires_once(self):
        t = Tracker(settle=2)
        t.update([ag("working")], 0)
        self.assertEqual(t.update([ag("blocked")], 10), [])
        self.assertEqual(t.update([ag("working")], 11), [])  # flicker, never reported
        t.update([ag("blocked")], 20)
        self.assertEqual([e[0] for e in t.update([ag("blocked")], 23)], ["blocked"])
        self.assertEqual(t.update([ag("blocked")], 30), [])

    def test_answered_question_then_done_counts_whole_turn(self):
        t = Tracker(min_work=20, settle=2)
        t.update([ag("working")], 0)
        t.update([ag("blocked")], 10)
        t.update([ag("blocked")], 13)
        t.update([ag("working")], 40)
        ev = t.update([ag("idle")], 100)
        self.assertEqual([e[0] for e in ev], ["done"])

    def test_unknown_is_ignored_and_closed_pane_forgotten(self):
        t = Tracker()
        t.update([ag("working")], 0)
        self.assertEqual(t.update([ag("unknown")], 50), [])
        t.update([], 60)
        self.assertEqual(t.panes, {})


class MessageTest(unittest.TestCase):
    SCREEN = "old output\n" + "\u2500" * 40 + "\n Test\n\n Question?\n 1. Yes\n 2. No\n" + "\u2500" * 40 + "\n footer\n"

    def test_dialog_between_last_separators(self):
        out = message.dialog_text(self.SCREEN)
        self.assertIn("Question?", out)
        self.assertNotIn("footer", out)
        self.assertNotIn("old output", out)

    def test_dialog_falls_back_to_tail(self):
        self.assertIn("plain", message.dialog_text("a\nplain\n"))

    def test_last_assistant_text_respects_since(self):
        def rec(role, text, ts):
            return json.dumps({"message": {"role": role, "timestamp": ts, "content": [{"type": "text", "text": text}]}})
        with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False) as f:
            f.write("\n".join([rec("assistant", "old", 1_000_000), rec("assistant", "fresh", 200_000_000), rec("user", "q", 300_000_000)]))
        try:
            self.assertEqual(message.last_assistant_text(f.name, 100_000), "fresh")
            self.assertEqual(message.last_assistant_text(f.name, 900_000), "")
            self.assertEqual(message.last_assistant_text("/nonexistent", 0), "")
        finally:
            os.unlink(f.name)

    def test_build(self):
        a = ag("blocked")
        self.assertTrue(message.build("blocked", a, "proj", 0, "Q?").startswith("ASKS: proj / proj (w1:p1)"))
        self.assertIn("1 min 5 s", message.build("done", a, "proj", 65, ""))


if __name__ == "__main__":
    unittest.main()
