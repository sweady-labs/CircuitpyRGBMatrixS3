"""German local time and the night window (app/clock.py), plain CPython:

    python3 -m unittest tests/test_clock.py
"""
import calendar
import unittest

from app import clock


def utc(*parts):
    return calendar.timegm(parts + (0,) * (6 - len(parts)))


class SummerTimeTests(unittest.TestCase):
    def test_winter_and_summer(self):
        self.assertEqual(clock.utc_offset(utc(2026, 1, 15, 12)), 3600)
        self.assertEqual(clock.utc_offset(utc(2026, 7, 1, 12)), 7200)

    def test_switch_in_march_happens_at_one_utc_on_the_last_sunday(self):
        # 29 March 2026 is the last Sunday in March
        self.assertEqual(clock.utc_offset(utc(2026, 3, 29, 0, 59, 59)), 3600)
        self.assertEqual(clock.utc_offset(utc(2026, 3, 29, 1, 0, 0)), 7200)

    def test_switch_in_october_happens_at_one_utc_on_the_last_sunday(self):
        # 25 October 2026 is the last Sunday in October
        self.assertEqual(clock.utc_offset(utc(2026, 10, 25, 0, 59, 59)), 7200)
        self.assertEqual(clock.utc_offset(utc(2026, 10, 25, 1, 0, 0)), 3600)

    def test_other_years(self):
        # 2027: 28 March and 31 October; 2030: 31 March and 27 October
        self.assertEqual(clock.utc_offset(utc(2027, 3, 28, 1)), 7200)
        self.assertEqual(clock.utc_offset(utc(2027, 10, 31, 0, 30)), 7200)
        self.assertEqual(clock.utc_offset(utc(2027, 10, 31, 1)), 3600)
        self.assertEqual(clock.utc_offset(utc(2030, 3, 31, 1)), 7200)
        self.assertEqual(clock.utc_offset(utc(2030, 10, 27, 1)), 3600)

    def test_new_year_is_winter_time(self):
        self.assertEqual(clock.utc_offset(utc(2026, 12, 31, 23, 30)), 3600)
        self.assertEqual(clock.utc_offset(utc(2027, 1, 1, 0, 30)), 3600)


class NightWindowTests(unittest.TestCase):
    def test_window_across_midnight(self):
        self.assertTrue(clock.in_window(clock.minutes("23:00"), "22:30", "06:30"))
        self.assertTrue(clock.in_window(clock.minutes("03:00"), "22:30", "06:30"))
        self.assertTrue(clock.in_window(clock.minutes("22:30"), "22:30", "06:30"))
        self.assertFalse(clock.in_window(clock.minutes("06:30"), "22:30", "06:30"))
        self.assertFalse(clock.in_window(clock.minutes("12:00"), "22:30", "06:30"))

    def test_window_on_the_same_day(self):
        self.assertTrue(clock.in_window(clock.minutes("13:00"), "12:00", "14:00"))
        self.assertFalse(clock.in_window(clock.minutes("14:00"), "12:00", "14:00"))

    def test_equal_start_and_end_is_never(self):
        self.assertFalse(clock.in_window(clock.minutes("08:00"), "08:00", "08:00"))


if __name__ == "__main__":
    unittest.main()
