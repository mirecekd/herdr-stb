# tests/test_ask.py
import unittest

from herdr_stb.ask import Ask


def mk(*qs):
    return Ask({"toolCallId": "call_1", "fname": "call_1.json", "questions": list(qs)}, "proj / x")


def q(text, n=3, multi=False):
    return {"question": text, "header": "h", "multiSelect": multi,
            "options": [{"label": "opt%d" % i, "description": "d%d" % i} for i in range(n)]}


class AskTest(unittest.TestCase):
    def test_single_select_by_button(self):
        a = mk(q("Q1"))
        self.assertEqual(a.press(a.key + ":0:o1"), ("submit", None))
        self.assertEqual(a.payload(), {"answers": [{"questionIndex": 0, "optionIndexes": [1]}]})

    def test_free_text_answer(self):
        a = mk(q("Q1"))
        self.assertEqual(a.text("  my own  ")[0], "submit")
        self.assertEqual(a.payload()["answers"][0], {"questionIndex": 0, "text": "my own"})

    def test_blank_text_ignored(self):
        a = mk(q("Q1"))
        self.assertEqual(a.text("   ")[0], "ignore")
        self.assertEqual(a.answers, [])

    def test_multi_select_toggle_done_and_text(self):
        a = mk(q("Q1", multi=True))
        self.assertEqual(a.press(a.key + ":0:o2")[0], "edit")
        self.assertEqual(a.press(a.key + ":0:o0")[0], "edit")
        self.assertEqual(a.press(a.key + ":0:o2")[0], "edit")  # untoggle
        self.assertEqual(a.text("extra")[0], "submit")
        self.assertEqual(a.payload()["answers"][0], {"questionIndex": 0, "optionIndexes": [0], "text": "extra"})

    def test_multi_done_needs_a_selection(self):
        a = mk(q("Q1", multi=True))
        self.assertEqual(a.press(a.key + ":0:d")[0], "ignore")

    def test_two_questions_in_order_and_stale_button(self):
        a = mk(q("Q1"), q("Q2"))
        self.assertEqual(a.press(a.key + ":0:o0")[0], "edit")
        self.assertEqual(a.q["question"], "Q2")
        self.assertEqual(a.press(a.key + ":0:o1")[0], "ignore")  # button of the answered question
        self.assertEqual(a.press(a.key + ":1:o2")[0], "submit")
        self.assertEqual([x["questionIndex"] for x in a.payload()["answers"]], [0, 1])

    def test_cancel(self):
        a = mk(q("Q1"))
        self.assertEqual(a.press(a.key + ":0:c")[0], "submit")
        self.assertEqual(a.payload(), {"cancel": True})

    def test_out_of_range_option_ignored(self):
        a = mk(q("Q1", n=2))
        self.assertEqual(a.press(a.key + ":0:o7")[0], "ignore")

    def test_view_fits_telegram_limits(self):
        a = mk(q("Q" * 50, n=12, multi=True))
        text, rows = a.view()
        self.assertLessEqual(len(text), 3900)
        self.assertTrue(all(len(b["callback_data"].encode()) <= 64 for r in rows for b in r))

    def test_summary(self):
        a = mk(q("Q1"))
        a.text("hello")
        self.assertIn('"hello"', a.summary())


if __name__ == "__main__":
    unittest.main()
