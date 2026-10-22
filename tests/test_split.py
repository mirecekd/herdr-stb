# tests/test_split.py
import unittest

from herdr_stb.mdhtml import md_to_html
from herdr_stb.split import MAX_PARTS, fits, parts


def strip_marker(p):
    return p.rsplit("\n\n(", 1)[0]


class SplitTest(unittest.TestCase):
    def test_short_text_is_one_untouched_part(self):
        self.assertEqual(parts("hello **x**"), ["hello **x**"])

    def test_empty_gives_no_parts(self):
        self.assertEqual(parts("  \n"), [])

    def test_every_part_fits_after_html_conversion(self):
        text = "\n\n".join("Odstavec %d: <tag> & **tucne** text s diakritikou ěščřžýáíé. " % i * 6 for i in range(60))
        ps = parts(text)
        self.assertGreater(len(ps), 1)
        for p in ps:
            self.assertLessEqual(len(md_to_html(p)), 4096)

    def test_cuts_at_paragraph_boundaries_and_numbers_parts(self):
        text = "\n\n".join("para %d " % i + "x" * 400 for i in range(20))
        ps = parts(text)
        self.assertTrue(ps[0].endswith("(1/%d)" % len(ps)))
        self.assertTrue(strip_marker(ps[0]).rstrip().endswith("x"))  # not in the middle of a word
        self.assertNotIn("(1/", ps[-1])

    def test_nothing_lost_below_the_part_limit(self):
        words = ["w%d" % i for i in range(1500)]
        text = " ".join(words)
        ps = parts(text)
        joined = " ".join(strip_marker(p) for p in ps)
        self.assertEqual(joined.split(), words)

    def test_code_fence_is_closed_and_reopened_across_parts(self):
        code = "```python\n" + "\n".join("line_%d = %d" % (i, i) for i in range(900)) + "\n```"
        ps = parts("intro\n\n" + code)
        self.assertGreater(len(ps), 1)
        for p in ps:
            self.assertEqual(strip_marker(p).count("```") % 2, 0, "unbalanced fence in a part")

    def test_text_without_any_break_is_still_split(self):
        ps = parts("a" * 12000)
        self.assertGreater(len(ps), 2)
        for p in ps:
            self.assertLessEqual(len(md_to_html(p)), 4096)

    def test_runaway_text_keeps_its_end_and_drops_the_middle(self):
        text = "\n\n".join("paragraph %d " % i + "y" * 500 for i in range(400)) + "\n\nTHE END?"
        ps = parts(text)
        self.assertLessEqual(len(ps), MAX_PARTS)
        self.assertIn("THE END?", ps[-1])
        self.assertTrue(any("left out" in p for p in ps))

    def test_html_heavy_text_is_shrunk_to_fit(self):
        text = "<&>" * 3000
        for p in parts(text):
            self.assertTrue(fits(strip_marker(p)) or len(p) < 300)


if __name__ == "__main__":
    unittest.main()
