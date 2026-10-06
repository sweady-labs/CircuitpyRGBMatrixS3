"""Time of day: NTP sync and German local time (CET/CEST).

The RTC keeps UTC. Local time is computed from it on every call, so the switch to and from
summer time happens exactly on time, not only at the next sync.

The pure functions (utc_offset, in_window, minutes) also run on a computer for the tests.
"""
import time

NTP_SERVER = "pool.ntp.org"
NTP_TO_UNIX = 2208988800
SYNC_EVERY = 6 * 3600
RETRY_AFTER = 60
VALID_AFTER = 1704067200  # 2024-01-01: before that the RTC was never set

WEEKDAYS = ("Mo", "Di", "Mi", "Do", "Fr", "Sa", "So")
MONTHS = ("Jan", "Feb", "Mär", "Apr", "Mai", "Jun", "Jul", "Aug", "Sep", "Okt", "Nov", "Dez")

_next_sync = 0


def _days_from_civil(y, m, d):
    """Days since 1970-01-01 (proleptic Gregorian calendar)."""
    y -= m <= 2
    era = y // 400
    yoe = y - era * 400
    doy = (153 * (m + (-3 if m > 2 else 9)) + 2) // 5 + d - 1
    doe = yoe * 365 + yoe // 4 - yoe // 100 + doy
    return era * 146097 + doe - 719468


def _year_of(days):
    z = days + 719468
    era = z // 146097
    doe = z - era * 146097
    yoe = (doe - doe // 1460 + doe // 36524 - doe // 146096) // 365
    doy = doe - (365 * yoe + yoe // 4 - yoe // 100)
    month = (5 * doy + 2) // 153
    return yoe + era * 400 + (1 if month >= 10 else 0)


def _last_sunday_1am_utc(year, month):
    last = _days_from_civil(year, month, 31)
    last -= (last + 4) % 7  # 1970-01-01 was a Thursday, (days + 4) % 7 == 0 is a Sunday
    return last * 86400 + 3600


def utc_offset(utc):
    """Seconds to add to UTC for German time: summer time from the last Sunday in March to the
    last Sunday in October, both at 01:00 UTC."""
    year = _year_of(utc // 86400)
    if _last_sunday_1am_utc(year, 3) <= utc < _last_sunday_1am_utc(year, 10):
        return 7200
    return 3600


def minutes(text):
    """ "06:30" -> 390"""
    hours, mins = text.split(":")
    return int(hours) * 60 + int(mins)


def in_window(now_minutes, start, end):
    """Is now_minutes (minutes after midnight) inside start-end ("HH:MM")? Works across midnight."""
    a = minutes(start)
    b = minutes(end)
    if a == b:
        return False
    if a < b:
        return a <= now_minutes < b
    return now_minutes >= a or now_minutes < b


def valid():
    return time.time() > VALID_AFTER


def now():
    """Local time as struct_time, or None while the clock was never synced."""
    if not valid():
        return None
    utc = time.time()
    return time.localtime(utc + utc_offset(utc))


def sync_if_due(pool):
    """Sync with NTP every SYNC_EVERY seconds, retry after RETRY_AFTER on failure. Blocks up to 2 s."""
    global _next_sync
    if time.monotonic() < _next_sync:
        return
    import rtc
    import struct

    try:
        address = pool.getaddrinfo(NTP_SERVER, 123)[0][4]
        sock = pool.socket(pool.AF_INET, pool.SOCK_DGRAM)
        sock.settimeout(2)
        packet = bytearray(48)
        packet[0] = 0x1B  # NTP version 3, client
        sock.sendto(packet, address)
        sock.recvfrom_into(packet)
        sock.close()
        seconds = struct.unpack_from("!I", packet, 40)[0] - NTP_TO_UNIX
        rtc.RTC().datetime = time.localtime(seconds)
        _next_sync = time.monotonic() + SYNC_EVERY
        print("[NTP] synced")
    except Exception as e:
        print("[NTP] failed: %s" % e)
        _next_sync = time.monotonic() + RETRY_AFTER
