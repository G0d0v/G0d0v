import importlib.util
from collections import Counter
from datetime import date
from pathlib import Path
import unittest

path = Path(__file__).resolve().parents[1] / "scripts" / "update_stats.py"
spec = importlib.util.spec_from_file_location("stats", path)
stats = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stats)


class StatsTests(unittest.TestCase):
    def test_current_streak_accepts_yesterday_and_excludes_future(self):
        days = [{"date": "2026-11-10", "contributionCount": 2},
                {"date": "2026-11-11", "contributionCount": 1},
                {"date": "2026-11-12", "contributionCount": 0},
                {"date": "2026-11-13", "contributionCount": 5}]
        self.assertEqual(stats.streaks(days, date(2026, 11, 12)), (2, 2))

    def test_missing_calendar_days_break_a_streak(self):
        days = [{"date": "2026-11-08", "contributionCount": 2},
                {"date": "2026-11-10", "contributionCount": 1},
                {"date": "2026-11-11", "contributionCount": 0},
                {"date": "2026-11-12", "contributionCount": 2}]
        self.assertEqual(stats.streaks(days, date(2026, 11, 12)), (1, 1))

    def test_exclude_private_profile_and_markup_from_languages(self):
        rows = [{"name": "product", "private": False,
                 "languages": {"Python": 50, "HTML": 9999, "TypeScript": 30}},
                {"name": "G0d0v", "private": False, "languages": {"Python": 1000}},
                {"name": "private", "private": True, "languages": {"Python": 2000}}]
        self.assertEqual(stats.language_totals(rows), {"Python": 50, "TypeScript": 30})

    def test_empty_calendar_and_languages_are_valid(self):
        from xml.etree import ElementTree
        self.assertEqual(stats.streaks([], date(2026, 11, 12)), (0, 0))
        ElementTree.fromstring(stats.languages_svg(Counter()))
        ElementTree.fromstring(stats.calendar_svg({"weeks": [], "totalContributions": 0}))


if __name__ == "__main__":
    unittest.main()
