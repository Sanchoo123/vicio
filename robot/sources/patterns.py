"""Ritmo habitual das marcas (Supreme às quintas, Palace às sextas) -> drops 'previstos'."""
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from ..config import BRANDS, PATTERN_DAYS_AHEAD, PATTERNS, TZ


def expected(now):
    out, today = [], now.date()
    for pat in PATTERNS:
        tz = ZoneInfo(pat["tz"])
        h, m = map(int, pat["time"].split(":"))
        seasons = [(date.fromisoformat(a), date.fromisoformat(b)) for a, b in pat["seasons"]]
        for i in range(PATTERN_DAYS_AHEAD + 1):
            d = today + timedelta(days=i)
            if d.weekday() != pat["weekday"] or not any(a <= d <= b for a, b in seasons):
                continue
            loc = datetime(d.year, d.month, d.day, h, m, tzinfo=tz).astimezone(TZ)
            b = pat["brand"]
            out.append(dict(id=f"{b}-{loc.date().isoformat()}", brand=b, name=pat["name"], date=loc.date().isoformat(),
                            time=loc.strftime("%H:%M"), status="previsto", method=BRANDS[b]["method"], image=None,
                            products=[], sources=[dict(name="Ritmo habitual da marca", url=BRANDS[b]["site"])],
                            origin="pattern"))
    return out
