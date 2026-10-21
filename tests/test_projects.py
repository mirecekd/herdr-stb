# tests/test_projects.py
import os
import tempfile
import time
import unittest
from unittest import mock

from herdr_stb import commands, projects


class ProjectsTest(unittest.TestCase):
    P = [("alpha", True), ("beta", False), ("tumor", True), ("tumor-docs", False), ("sw-tumor", True), ("zeta", True)]

    def test_scan_newest_first_and_marks_git(self):
        with tempfile.TemporaryDirectory() as d:
            for i, (name, git) in enumerate([("old", True), ("new", False)]):
                os.makedirs(os.path.join(d, name, ".git" if git else "x"))
                os.utime(os.path.join(d, name), (time.time() - 100 + i * 50,) * 2)
            os.makedirs(os.path.join(d, ".hidden"))
            open(os.path.join(d, "file.txt"), "w").close()
            self.assertEqual(projects.scan(d), [("new", False), ("old", True)])
        self.assertEqual(projects.scan("/nonexistent/x"), [])

    def test_recent_puts_running_first_then_git_only(self):
        r = projects.recent(self.P, {"zeta", "beta"})
        self.assertEqual([n for n, _ in r][:2], ["beta", "zeta"])
        self.assertNotIn("tumor-docs", [n for n, _ in r])  # not git, not running

    def test_recent_is_capped(self):
        many = [("p%d" % i, True) for i in range(30)]
        self.assertEqual(len(projects.recent(many, set())), projects.RECENT)

    def test_search_prefix_first_then_git_then_short(self):
        self.assertEqual([n for n, _ in projects.search(self.P, "tum")], ["tumor", "tumor-docs", "sw-tumor"])
        self.assertEqual(projects.search(self.P, "  "), [])
        self.assertEqual(projects.search(self.P, "TUMOR")[0][0], "tumor")

    def test_search_is_capped(self):
        many = [("app%d" % i, True) for i in range(40)]
        self.assertEqual(len(projects.search(many, "app")), projects.SEARCH_MAX)

    def test_button_data_fits_telegram_limit(self):
        long = [("x" * 50, True)]
        for text, rows in (projects.home(long, set()), projects.results(long, "x"), projects.kind_screen("x" * 50, ["pi"], "pi")):
            for r in rows:
                for b in r:
                    self.assertLessEqual(len(b["callback_data"].encode()), 64)
                    self.assertLessEqual(len(b["text"]), 60)

    def test_results_without_hits_offers_only_cancel(self):
        text, rows = projects.results([], "zzz")
        self.assertIn("zzz", text)
        self.assertEqual(len(rows), 1)

    def test_kind_screen_puts_last_used_first(self):
        _, rows = projects.kind_screen("p", ["pi", "claude", "gemini"], "claude")
        self.assertEqual(rows[0][0]["callback_data"], "N:k:claude")
        self.assertIn("last used", rows[0][0]["text"])

    def test_safe_name_rejects_paths(self):
        for bad in ("", ".", "..", "../etc", "a/b", "/abs"):
            self.assertFalse(projects.safe_name(bad), bad)
        self.assertTrue(projects.safe_name("my-proj.v2"))

    def test_installed_kinds_uses_path(self):
        with mock.patch("shutil.which", lambda k: "/bin/" + k if k in ("pi", "claude") else None):
            self.assertEqual(projects.installed_kinds(), ["pi", "claude"])


class CommandsTest(unittest.TestCase):
    def test_parse(self):
        self.assertEqual(commands.parse("/Windows@my_bot extra"), "windows")
        self.assertEqual(commands.parse("/new"), "new")
        self.assertEqual(commands.parse("hello /new"), "")

    def test_unreserved_command_is_not_handled(self):
        self.assertFalse(commands.handle({}, "compact", None, None))

    def test_new_starts_the_picker(self):
        called = []
        new = mock.Mock(begin=lambda: called.append(1))
        self.assertTrue(commands.handle({}, "new", None, new))
        self.assertEqual(called, [1])

    def test_menu_lists_all_commands(self):
        self.assertEqual([c for c, _ in commands.COMMANDS], ["windows", "new", "on", "off"])


if __name__ == "__main__":
    unittest.main()
