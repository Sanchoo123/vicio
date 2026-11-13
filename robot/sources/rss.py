"""Notícias por RSS (Hypebeast, Sneaker News, Nice Kicks) -> novidades e drops com data."""
import hashlib
import re
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

from ..config import BRANDS, TZ
from ..text import clean_title, detect_brand, find_date, find_time, slugify, strip_html

CONTENT = "{http://purl.org/rss/1.0/modules/content/}encoded"
MEDIA = "{http://search.yahoo.com/mrss/}content"
IMG_RE = re.compile(r"<img[^>]+src=[\"']([^\"']+)[\"']", re.I)
BAD_IMG = re.compile(r"\.svg(?:$|\?)|logo|icon|avatar|gravatar|emoji|pixel|spacer|1x1", re.I)
DROPLIST_RE = re.compile(r"\bdrop\s?list\b|\bweek\s+\d{1,2}\b|\bthis week'?s drop\b", re.I)


def _image(it, *htmls):
    cands = []
    m = it.find(MEDIA)
    if m is not None and m.get("url"):
        cands.append(m.get("url"))
    enc = it.find("enclosure")
    if enc is not None and (enc.get("type") or "").startswith("image") and enc.get("url"):
        cands.append(enc.get("url"))
    for h in htmls:
        cands += IMG_RE.findall(h or "")
    for u in cands:  # primeira foto a sério (sem logótipos nem ícones)
        if u.startswith("http") and not BAD_IMG.search(u.split("/")[-1]):
            return u
    return None


def parse_feed(xml_bytes, feed_name, today, gnews=False):
    """Devolve itens {id, brand, title, url, image, published, source, date?, time?, date_in_title, droplist}.

    gnews=True: feed do Google Notícias, onde o título acaba em " - Site" e o site vem em <source>."""
    root = ET.fromstring(xml_bytes)
    out = []
    for it in root.iter("item"):
        title = strip_html(it.findtext("title"))
        source = feed_name
        if gnews:
            site = (it.findtext("source") or "").strip()
            if site:
                source = site
                if title.endswith(" - " + site):
                    title = title[: -len(site) - 3].strip()
        link = (it.findtext("link") or "").strip()
        desc_html = it.findtext("description") or ""
        content_html = it.findtext(CONTENT) or ""
        cats = [c.text or "" for c in it.findall("category")]
        brand = detect_brand(" | ".join([title] + cats))
        if not brand:
            continue
        text = "" if gnews else strip_html(desc_html)[:900]  # no Google Notícias a descrição só repete o título
        d = find_date(title, today)
        in_title = d is not None
        if not d:
            d = find_date(text, today)
        if BRANDS[brand].get("dated_only") and not d:
            continue
        pub = None
        try:
            pub = parsedate_to_datetime(it.findtext("pubDate")).astimezone(TZ).isoformat(timespec="minutes")
        except (TypeError, ValueError):
            pass
        guid = (it.findtext("guid") or link or title).strip()
        item = dict(id=hashlib.sha1(guid.encode()).hexdigest()[:12], brand=brand, title=title, url=link,
                    image=None if gnews else _image(it, desc_html, content_html), published=pub, source=source,
                    date_in_title=in_title, droplist=bool(DROPLIST_RE.search(title)))
        if d:
            item["date"] = d.isoformat()
            t = find_time(title + " " + text, d)
            if t and t[0] == d:
                item["time"] = t[1]
        out.append(item)
    return out


def to_drop(item):
    """Notícia com data -> drop."""
    b = item["brand"]
    did = f"{b}-{item['date']}"
    if b == "nike":  # a Nike lança vários modelos no mesmo dia
        did += "-" + slugify(clean_title(item["title"]))
    return dict(id=did, brand=b, name=clean_title(item["title"]), date=item["date"], time=item.get("time"),
                status="confirmado" if item["date_in_title"] else "rumor", method=BRANDS[b]["method"],
                image=item.get("image"), products=[],
                sources=[dict(name=item["source"], url=item["url"])], origin="rss")
