"""
hub_lines.py - Turns the home hub summary (/api/zusammenfassung) into three display lines.

Plain Python without CircuitPython modules, so it can be tested on a computer:
    python3 -m unittest tests/test_hub_lines.py
"""

GREEN = 0x00AA00
YELLOW = 0xAA7700
RED = 0xCC0000
BLUE = 0x0044CC
GREY = 0x444444

# backup.status from the hub -> line on the matrix
BACKUP = {
    "ok": ("Backup ok", GREEN),
    "laeuft": ("Backup ...", BLUE),
    "veraltet": ("Backup alt", YELLOW),
    "fehlgeschlagen": ("Backup !!", RED),
    "haengt": ("Backup !!", RED),
    "nicht_eingerichtet": ("Backup -", GREY),
}


def status_lines(result):
    """Three (text, color) pairs: internet, backup, hints. At most 10 characters each (64 px, 6 px font).

    result is the parsed JSON from the hub, or a short error text if the request failed.
    """
    if not isinstance(result, dict):
        return [("Hub weg", RED), (str(result)[:10], GREY), ("", GREY)]

    internet = result.get("internet") or {}
    online = internet.get("online")
    if online is False:
        net = ("Offline", RED)
    elif online is None:
        net = ("Internet ?", GREY)
    elif internet.get("download_mbit"):
        net = ("%d Mbit" % round(internet["download_mbit"]), GREEN)
    else:
        net = ("Online", GREEN)

    backup = BACKUP.get((result.get("backup") or {}).get("status"), ("Backup ?", GREY))

    status = result.get("status")
    count = result.get("anzahl_hinweise") or 0
    if status == "ok":
        hints = ("Alles ok", GREEN)
    elif status in ("hinweise", "problem"):
        text = "1 Hinweis" if count == 1 else "%d Hinweise" % count
        hints = (text, RED if status == "problem" else YELLOW)
    else:
        hints = ("Status ?", GREY)

    return [net, backup, hints]
