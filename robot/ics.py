"""Ficheiros de calendário (.ics) para subscrever na app Calendário do iPhone."""
from datetime import date, datetime, timedelta, timezone

from .config import BRANDS, TZ


def _esc(s):
    return (s or "").replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def _fold(line):
    out, b = [], line.encode()
    while len(b) > 74:
        cut = 74
        while (b[cut] & 0xC0) == 0x80:  # não partir caracteres UTF-8 a meio
            cut -= 1
        out.append(b[:cut].decode())
        b = b" " + b[cut:]
    out.append(b.decode())
    return "\r\n".join(out)


def build(drops, name, alarms=False):
    L = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Vicio//Drops//PT", "CALSCALE:GREGORIAN",
         "METHOD:PUBLISH", f"X-WR-CALNAME:{_esc(name)}", "X-WR-TIMEZONE:Europe/Lisbon",
         "REFRESH-INTERVAL;VALUE=DURATION:PT1H"]
    for d in drops:
        day = date.fromisoformat(d["date"])
        brand = BRANDS[d["brand"]]["name"]
        status = {"previsto": " (previsto)", "rumor": " (rumor)"}.get(d["status"], "")
        L += ["BEGIN:VEVENT", f"UID:{d['id']}@vicio", f"DTSTAMP:{day:%Y%m%d}T000000Z"]
        if d.get("time"):
            h, m = map(int, d["time"].split(":"))
            start = datetime(day.year, day.month, day.day, h, m, tzinfo=TZ).astimezone(timezone.utc)
            L += [f"DTSTART:{start:%Y%m%dT%H%M%SZ}", f"DTEND:{start + timedelta(minutes=30):%Y%m%dT%H%M%SZ}"]
        else:
            L += [f"DTSTART;VALUE=DATE:{day:%Y%m%d}", f"DTEND;VALUE=DATE:{day + timedelta(days=1):%Y%m%d}"]
        desc = [d["name"], f"Método: {d.get('method') or '?'}"] + [f"{s['name']}: {s['url']}" for s in d.get("sources", [])]
        L += [f"SUMMARY:{_esc(brand + ' · ' + d['name'] + status)}", f"DESCRIPTION:{_esc(chr(10).join(desc))}"]
        if d.get("sources"):
            L.append(f"URL:{d['sources'][0]['url']}")
        if alarms and d.get("time"):
            for mins, txt in ((60, "Drop daqui a 1 hora"), (10, "10 minutos: faz login")):
                L += ["BEGIN:VALARM", "ACTION:DISPLAY", f"DESCRIPTION:{_esc(brand + ' — ' + txt)}",
                      f"TRIGGER:-PT{mins}M", "END:VALARM"]
        L.append("END:VEVENT")
    L.append("END:VCALENDAR")
    return "\r\n".join(_fold(x) for x in L) + "\r\n"
