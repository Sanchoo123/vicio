"""Calendário oficial SNKRS da Nike Portugal (os dados que alimentam nike.com/pt/launch).

Dá a hora exata em Portugal, o preço em euros, o tipo de venda (FCFS ou sorteio) e as fotos.
Os lançamentos da mesma hora juntam-se num só drop com várias peças."""
from datetime import datetime

from ..config import NIKE_FEED, TZ
from ..http import get_json
from ..text import detect_brand

METHOD = {"LEO": "SNKRS · FCFS", "DAN": "SNKRS · SORTEIO"}


def _clean(s):
    return " ".join((s or "").replace("\xa0", " ").split())


def _when(iso):
    return datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(TZ)


def parse(doc):
    """doc: resposta do feed -> lista de drops."""
    groups = {}
    for o in doc.get("objects", []):
        props = (o.get("publishedContent") or {}).get("properties") or {}
        cover = (props.get("coverCard") or {}).get("properties") or {}
        model, color = _clean(cover.get("subtitle")), _clean(cover.get("title"))
        name = f"{model} “{color}”" if model and color and color != model else model or _clean(props.get("title"))
        slug = (props.get("seo") or {}).get("slug")
        url = f"https://www.nike.com/pt/launch/t/{slug}" if slug else "https://www.nike.com/pt/launch"
        img = cover.get("squarishURL") or cover.get("portraitURL") or None
        for p in o.get("productInfo") or []:
            mp, price, lv = p.get("merchProduct") or {}, p.get("merchPrice") or {}, p.get("launchView") or {}
            start = lv.get("startEntryDate") or mp.get("commerceStartDate")
            if not start or price.get("currentPrice") is None or mp.get("status") != "ACTIVE":
                continue  # sem data ou sem preço (ex.: episódios do "SNKRS Service")
            t = _when(start)
            title = _clean((p.get("productContent") or {}).get("fullTitle")) or name
            brand = detect_brand(name) or "nike"  # Corteiz x Nike conta para a Corteiz
            method = METHOD.get(lv.get("method"), "NIKE.COM")
            if lv.get("method") == "DAN" and lv.get("stopEntryDate"):
                method += f" até {_when(lv['stopEntryDate']):%d/%m %H:%M}"
            key = (brand, t.date().isoformat(), t.strftime("%H:%M"))
            g = groups.setdefault(key, dict(method=method, products=[], urls=[], names=[], image=img))
            if any(x["sku"] == mp.get("styleColor") for x in g["products"]):
                continue  # o mesmo par repetido em duas páginas
            g["products"].append(dict(name=name if len(o.get("productInfo")) == 1 else title,
                                      color=_clean((p.get("productContent") or {}).get("colorDescription")),
                                      price=float(price["currentPrice"]), currency=price.get("currency") or "EUR",
                                      image=img, url=url, sku=mp.get("styleColor")))
            if url not in g["urls"]:
                g["urls"].append(url)
                g["names"].append(name)
    drops = []
    for (brand, d, hm), g in sorted(groups.items(), key=lambda kv: kv[0][1:]):
        prods, n = g["products"], len(g["urls"])
        first = g["names"][0]
        drops.append(dict(id=f"{brand}-{d}-snkrs-{hm.replace(':', '')}", brand=brand,
                          name=first if n == 1 else f"{first} + {n - 1} {'lançamento' if n == 2 else 'lançamentos'}",
                          date=d, time=hm, status="confirmado", method=g["method"], image=g["image"], products=prods,
                          sources=[dict(name="Nike SNKRS Portugal", url=g["urls"][0] if n == 1 else "https://www.nike.com/pt/launch?s=upcoming")],
                          origin="nike"))
    return drops


def fetch():
    return parse(get_json(NIKE_FEED))
