# tests/test_mdhtml.py
import unittest

from herdr_stb.mdhtml import md_to_html


class MdHtmlTest(unittest.TestCase):
    def test_bold_and_heading(self):
        self.assertEqual(md_to_html("co udelej: **tucne** a dal"), "co udelej: <b>tucne</b> a dal")
        self.assertEqual(md_to_html("## Nadpis **x**"), "<b>Nadpis x</b>")

    def test_html_in_text_is_escaped(self):
        self.assertEqual(md_to_html("a < b & <script>"), "a &lt; b &amp; &lt;script&gt;")

    def test_code_is_protected_from_other_rules(self):
        self.assertEqual(md_to_html("`**x** <y>`"), "<code>**x** &lt;y&gt;</code>")
        self.assertEqual(md_to_html("```py\nprint('<a>')\n```"), "<pre>print('&lt;a&gt;')</pre>")

    def test_link(self):
        self.assertEqual(md_to_html("[doc](https://x.cz/a?b=1)"), '<a href="https://x.cz/a?b=1">doc</a>')
        self.assertEqual(md_to_html("[bad](javascript:alert(1))"), "[bad](javascript:alert(1))")

    def test_table_becomes_aligned_pre_block(self):
        md = "Pred\n\n| Funkce | Stav |\n|---|:-:|\n| **/windows** | ok |\n| `/on` | vypnuto |\n\nPo"
        out = md_to_html(md)
        self.assertEqual(out, "Pred\n\n<pre>Funkce    Stav\n--------  -------\n/windows  ok\n/on       vypnuto</pre>\n\nPo")

    def test_table_cells_are_escaped_and_ragged_rows_padded(self):
        out = md_to_html("| a | b |\n|--|--|\n| <x> |\n| 1 | 2 | 3 |")
        self.assertIn("&lt;x&gt;", out)
        self.assertEqual(out.count("\n"), 3)

    def test_pipe_without_separator_is_not_a_table(self):
        self.assertEqual(md_to_html("a | b\nc | d"), "a | b\nc | d")

    def test_plain_text_and_stray_markers_unchanged(self):
        self.assertEqual(md_to_html("ASKS: proj [1/2]\n1. Ano"), "ASKS: proj [1/2]\n1. Ano")
        self.assertEqual(md_to_html("jen ** jedna"), "jen ** jedna")


if __name__ == "__main__":
    unittest.main()
