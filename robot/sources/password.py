"""Lojas fechadas com palavra-passe entre drops (ex.: Vigilance, Corteiz).

Só se lê a página pública que qualquer visitante vê. Dá duas coisas:
- a data que a marca anuncia nessa página (ex.: "NEW DROP: 21.11.2026") -> drop confirmado;
- quando a página de palavra-passe desaparece -> a loja abriu (drop a decorrer)."""
import re
from datetime import date, timedelta

from ..config import WINDOW_DAYS
from ..http import get
from ..text import strip_html

DATE_RE = re.compile(r"(?<![\d.])(\d{1,2})[./-](\d{1,2})[./-](20\d\d)(?![\d.])")
TIME_RE = re.compile(r"^[^\d]{0,15}?(\d{1,2})\s*(?::|h)\s*(\d{2})?(?!\d)", re.I)


def is_locked(html):
    return 'action="/password"' in html or "template-password" in html


def page_text(html):
    html = re.sub(r"<(script|style)\b.*?</\1>", " ", html, flags=re.S | re.I)
    return strip_html(html)


def announced(text, today):
    """Primeira data dd.mm.aaaa (de ontem até WINDOW_DAYS) e, se vier logo a seguir, a hora."""
    for m in DATE_RE.finditer(text):
        try:
            d = date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        except ValueError:
            continue
        if not today - timedelta(days=1) <= d <= today + timedelta(days=WINDOW_DAYS):
            continue
        t = TIME_RE.match(text[m.end():m.end() + 30])
        hm = None
        if t and int(t.group(1)) < 24 and int(t.group(2) or 0) < 60:
            hm = f"{int(t.group(1)):02d}:{int(t.group(2) or 0):02d}"
        return d, hm
    return None, None


def check(store, st, now, name):
    """Devolve (drop ou None, eventos, aberta?)."""
    html = get(store["url"]).decode("utf-8", "ignore")
    locked, events, drop = is_locked(html), [], None
    if st.get("locked") is True and not locked:
        events.append(dict(type="store_open", brand=store["brand"], url=store["url"]))
    st["locked"] = locked
    if locked:
        d, hm = announced(page_text(html), now.date())
        if d:
            drop = dict(id=f"{store['brand']}-{d.isoformat()}", brand=store["brand"], name="Novo drop",
                        date=d.isoformat(), time=hm, status="confirmado", method="FCFS", image=None, products=[],
                        sources=[dict(name=f"Página da loja {name}", url=store["url"])], origin="shopify")
    return drop, events, not locked
