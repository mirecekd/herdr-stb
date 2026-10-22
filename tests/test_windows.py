# tests/test_windows.py
import unittest

from herdr_stb import windows


def ag(pane, ws, st="idle", cwd="/x/proj", kind="pi"):
    return {"pane_id": pane, "workspace_id": ws, "agent_status": st, "cwd": cwd, "agent": kind}


class WindowsTest(unittest.TestCase):
    WS = {"w1": "proj-a", "w2": "proj-b"}

    def test_label_is_workspace_when_unique(self):
        n = windows.labels([ag("w1:p1", "w1"), ag("w2:p1", "w2")], self.WS)
        self.assertEqual(n, {"w1:p1": "proj-a", "w2:p1": "proj-b"})

    def test_labels_disambiguate_by_folder_then_pane(self):
        n = windows.labels([ag("w1:p1", "w1", cwd="/a/x"), ag("w1:p2", "w1", cwd="/a/y")], self.WS)
        self.assertEqual(sorted(n.values()), ["proj-a/x", "proj-a/y"])
        n = windows.labels([ag("w1:p1", "w1", cwd="/a/x"), ag("w1:p2", "w1", cwd="/b/x")], self.WS)
        self.assertEqual(sorted(n.values()), ["proj-a/x w1:p1", "proj-a/x w1:p2"])

    def test_matrix_two_per_row_with_status_and_kind(self):
        text, rows = windows.matrix([ag("w1:p1", "w1", "working", kind="claude"), ag("w2:p1", "w2", "blocked"),
                                     ag("w2:p2", "w2", cwd="/q/z")], self.WS)
        self.assertEqual([len(r) for r in rows], [2, 1])
        self.assertEqual(rows[0][0]["text"], "proj-a (claude) - working")
        self.assertEqual(rows[0][0]["callback_data"], "W:a:w1:p1")
        self.assertIn("3", text)

    def test_callback_data_fits_telegram_limit(self):
        _, rows = windows.matrix([ag("w1AB:p123", "w1AB")], self.WS)
        self.assertLessEqual(len(rows[0][0]["callback_data"].encode()), 64)

    def test_empty_matrix(self):
        self.assertEqual(windows.matrix([], {})[1], [])

    def test_tail_trims_collapses_and_limits(self):
        s = "\n\n\nfirst\n\n\n\nsecond   \n\n\n"
        self.assertEqual(windows.tail(s), "first\n\nsecond")
        big = "\n".join("line %d" % i for i in range(500))
        self.assertEqual(len(windows.tail(big).splitlines()), windows.LINES)
        self.assertLessEqual(len(windows.tail("x" * 10000)), windows.CHARS)
        self.assertEqual(windows.tail("   \n\n"), "(empty)")

    def test_code_fence_in_screen_cannot_break_the_block(self):
        text, _ = windows.live("w", "pi", "idle", "a ``` b")
        self.assertEqual(text.count("```"), 2)

    def test_live_has_navigation_keys(self):
        _, rows = windows.live("w", "pi", "idle", "x")
        data = [b["callback_data"] for r in rows for b in r]
        self.assertIn("W:k:enter", data)
        self.assertIn("W:l", data)
        self.assertIn("W:d", data)


if __name__ == "__main__":
    unittest.main()
