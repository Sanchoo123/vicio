"""Google Notícias (RSS público de pesquisa): artigos de muitos sites sobre cada marca."""
import re
import urllib.parse

from ..config import GNEWS, GNEWS_KEEP_UNDATED, GNEWS_URL
from ..http import get
from . import rss

_WORD = re.compile(r"[a-z0-9]+")


def _key(title):
    """Chave grosseira para juntar o mesmo assunto contado por sites diferentes."""
    w = [x for x in _WORD.findall(title.lower()) if len(x) > 2][:6]
    return " ".join(sorted(w))


def fetch(today):
    """Devolve (itens, erros). Cada item é como os do rss.parse_feed, com quiet=True (não avisa)."""
    out, errs, seen = [], [], set()
    for g in GNEWS:
        try:
            items = rss.parse_feed(get(GNEWS_URL + urllib.parse.quote(g["q"])), "Google Notícias", today, gnews=True)
        except Exception as e:  # Blocked incluído: tenta-se outra vez na ronda seguinte
            errs.append(f"{g['brand']}: {e}")
            continue
        undated = 0
        for i in items:
            k = (i["brand"], i.get("date")) if i.get("date") else (i["brand"], _key(i["title"]))
            if k in seen:
                continue
            if not i.get("date") and not i["droplist"]:
                if undated >= GNEWS_KEEP_UNDATED:
                    continue
                undated += 1
            seen.add(k)
            i["quiet"] = True
            out.append(i)
    return out, errs
