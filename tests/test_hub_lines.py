"""Tests for app/hub_lines.py, run on a computer with plain CPython:

    python3 -m unittest tests/test_hub_lines.py

The sample answer follows build_summary() in sweady-labs/home-hub (dashboard/api.py).
"""
import json
import unittest

from app.hub_lines import GREEN, GREY, RED, YELLOW, status_lines

ALL_FINE = json.loads("""
{
  "stand": "2026-10-06T12:00:00+02:00",
  "status": "ok",
  "status_text": "Alles läuft",
  "anzahl_hinweise": 0,
  "satz": "212 Mbit/s, heute keine Ausfälle, Backup in Ordnung.",
  "internet": {"online": true, "download_mbit": 212.4, "upload_mbit": 40.2, "ping_ms": 11.3,
               "gemessen": "2026-10-06T11:50:00+02:00", "ausfaelle_heute": 0, "ausfallzeit_heute_s": 0},
  "backup": {"status": "ok", "text": "Backup in Ordnung", "letzter_erfolg": "2026-10-06T03:00:00+02:00",
             "auf_dem_mac": "2026-10-06T08:00:00+02:00"},
  "kita": null,
  "hinweise": []
}
""")


def summary(**changes):
    data = json.loads(json.dumps(ALL_FINE))
    for key, value in changes.items():
        if isinstance(value, dict):
            data[key].update(value)
        else:
            data[key] = value
    return data


class StatusLinesTests(unittest.TestCase):
    def test_everything_fine(self):
        self.assertEqual(status_lines(ALL_FINE), [("212 Mbit", GREEN), ("Backup ok", GREEN), ("Alles ok", GREEN)])

    def test_internet_down(self):
        data = summary(internet={"online": False}, status="problem", anzahl_hinweise=1)
        self.assertEqual(status_lines(data), [("Offline", RED), ("Backup ok", GREEN), ("1 Hinweis", RED)])

    def test_online_without_speed_test(self):
        self.assertEqual(status_lines(summary(internet={"download_mbit": None}))[0], ("Online", GREEN))

    def test_no_measurements_yet(self):
        data = summary(internet={"online": None, "download_mbit": None},
                       backup={"status": "nicht_eingerichtet", "text": ""}, status="hinweise", anzahl_hinweise=1)
        self.assertEqual(status_lines(data), [("Internet ?", GREY), ("Backup -", GREY), ("1 Hinweis", YELLOW)])

    def test_failed_backup_and_stopped_container(self):
        data = summary(backup={"status": "fehlgeschlagen"}, status="problem", anzahl_hinweise=2)
        self.assertEqual(status_lines(data)[1:], [("Backup !!", RED), ("2 Hinweise", RED)])

    def test_old_backup_is_a_warning(self):
        data = summary(backup={"status": "veraltet"}, status="hinweise", anzahl_hinweise=1)
        self.assertEqual(status_lines(data)[1:], [("Backup alt", YELLOW), ("1 Hinweis", YELLOW)])

    def test_unknown_values(self):
        self.assertEqual(status_lines({}), [("Internet ?", GREY), ("Backup ?", GREY), ("Status ?", GREY)])

    def test_hub_not_reachable(self):
        self.assertEqual(status_lines("keine Antw"), [("Hub weg", RED), ("keine Antw", GREY), ("", GREY)])
        self.assertEqual(status_lines("HTTP 401")[1], ("HTTP 401", GREY))

    def test_every_line_fits_on_the_matrix(self):
        cases = [ALL_FINE, {}, "keine Antw", summary(internet={"download_mbit": 1000.0}),
                 summary(status="problem", anzahl_hinweise=9)]
        cases += [summary(backup={"status": s}) for s in
                  ("ok", "laeuft", "fehlgeschlagen", "haengt", "veraltet", "nicht_eingerichtet")]
        for data in cases:
            for text, _ in status_lines(data):
                self.assertLessEqual(len(text), 10, text)


if __name__ == "__main__":
    unittest.main()
