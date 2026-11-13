"""Ler texto de notícias: marca, data e hora de lançamento."""
import html
import re
import unicodedata
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from .config import BRANDS, TZ, WINDOW_DAYS

_TAG = re.compile(r"<[^>]+>")


def strip_html(s):
    return re.sub(r"\s+", " ", html.unescape(_TAG.sub(" ", s or ""))).strip()


def slugify(s, n=5):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    words = [w for w in re.findall(r"[a-z0-9]+", s) if w not in {"the", "a", "of", "on", "in", "to", "and", "x"}]
    return "-".join(words[:n])


# ---------- marca ----------
_BRAND_RE = {k: [re.compile(p, 0 if b["case"] else re.I) for p in b["match"]] for k, b in BRANDS.items()}


def detect_brand(text):
    hits = [k for k, pats in _BRAND_RE.items() if any(p.search(text) for p in pats)]
    if len(hits) > 1 and "nike" in hits:  # colaboração (ex.: Stüssy x Nike) conta para a marca de streetwear
        hits.remove("nike")
    return hits[0] if hits else None


# ---------- data ----------
MONTHS = {"january": 1, "jan": 1, "february": 2, "feb": 2, "march": 3, "mar": 3, "april": 4, "apr": 4,
          "may": 5, "june": 6, "jun": 6, "july": 7, "jul": 7, "august": 8, "aug": 8, "september": 9,
          "sept": 9, "sep": 9, "october": 10, "oct": 10, "november": 11, "nov": 11, "december": 12, "dec": 12}
_MON = "January|February|March|April|May|June|July|August|September|October|November|December|Sept|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec"
DATE_RE = re.compile(rf"\b({_MON})\.?\s+(\d{{1,2}})(?:st|nd|rd|th)?\b(?:,?\s+(20\d\d))?", re.I)
# "Updated November 11th, 2026:" é a data da atualização do artigo, não do lançamento
UPDATED_RE = re.compile(rf"\bupdated?\b\W{{0,3}}(?:on\s+)?(?:{_MON})\.?\s+\d{{1,2}}(?:st|nd|rd|th)?(?:,?\s+20\d\d)?:?", re.I)


def _year_for(mon, day, today):
    for y in (today.year, today.year + 1):
        try:
            if date(y, mon, day) >= today - timedelta(days=7):
                return y
        except ValueError:
            return None
    return today.year + 1


def find_date(text, today):
    """Primeira data de lançamento plausível (de ontem até WINDOW_DAYS à frente)."""
    text = UPDATED_RE.sub(" ", text or "")
    for m in DATE_RE.finditer(text):
        mon_s = m.group(1)
        if mon_s.lower() == "may" and mon_s != "May":  # "may" verbo, não o mês
            continue
        mon, day = MONTHS[mon_s.lower()], int(m.group(2))
        year = int(m.group(3)) if m.group(3) else _year_for(mon, day, today)
        if not year:
            continue
        try:
            d = date(year, mon, day)
        except ValueError:
            continue
        if today - timedelta(days=1) <= d <= today + timedelta(days=WINDOW_DAYS):
            return d
    return None


# ---------- hora ----------
TIME_RE = re.compile(r"\b(\d{1,2})(?::(\d{2}))?\s*(a\.?m\.?|p\.?m\.?)\s*(ET|EST|EDT|PT|PST|PDT|GMT|BST|UK|CET|CEST|JST)\b", re.I)
_TZ = {"ET": "America/New_York", "EST": "America/New_York", "EDT": "America/New_York",
       "PT": "America/Los_Angeles", "PST": "America/Los_Angeles", "PDT": "America/Los_Angeles",
       "GMT": "Europe/London", "BST": "Europe/London", "UK": "Europe/London",
       "CET": "Europe/Paris", "CEST": "Europe/Paris", "JST": "Asia/Tokyo"}


def find_time(text, d):
    """Hora com fuso explícito (ex.: '10 a.m. ET'), convertida para Lisboa. Devolve (data, 'HH:MM') ou None."""
    m = TIME_RE.search(text or "")
    if not m:
        return None
    h, mi = int(m.group(1)), int(m.group(2) or 0)
    if h > 12 or mi > 59:
        return None
    pm = m.group(3).lower().startswith("p")
    h = (h % 12) + (12 if pm else 0)
    src = datetime(d.year, d.month, d.day, h, mi, tzinfo=ZoneInfo(_TZ[m.group(4).upper()]))
    loc = src.astimezone(TZ)
    return loc.date(), loc.strftime("%H:%M")


_PREFIX = re.compile(r"^(?:where to buy|official images of|first look at|detailed look at|on-?foot look at|"
                     r"official look at|closer look at|a closer look at)\s+(?:the\s+)?", re.I)


# "... Launches On November 20th" / "... Release Date & Info": a data já aparece noutro sítio da app
_SUFFIX = re.compile(r"\s+(?:(?:is\s+)?(?:reportedly\s+)?(?:launch|launches|launching|release|releases|releasing|drops|dropping|"
                     r"arrives|returns|restocks)\b.*|(?:(?:January|February|March|April|May|June|July|August|September|October|November|"
                     r"December)\s+)?(?:\d{4}\s+)?release date.*|[-–:]\s*(?:release|where to buy).*)$", re.I)


def clean_title(t):
    t = _PREFIX.sub("", t).strip()
    short = _SUFFIX.sub("", t).strip()
    return (short if len(short) >= 8 else t)[:90]
