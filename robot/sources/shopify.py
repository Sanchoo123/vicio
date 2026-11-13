"""Lojas com catálogo público (products.json): peças novas, fotos, preços e restocks."""
from ..config import BRANDS
from ..http import get_json


def map_product(p, store):
    v = p.get("variants") or [{}]
    img = (p.get("images") or [{}])[0].get("src")
    price = None
    try:
        price = float(v[0].get("price"))
    except (TypeError, ValueError):
        pass
    return dict(name=p.get("title", ""), price=price, currency=store.get("currency"), image=img,
                url=f"{store['url']}/products/{p.get('handle')}",
                available=any(x.get("available") for x in v), handle=p.get("handle"))


def check_store(store, st, watch_handles, now):
    """Lê a loja uma vez. Devolve (drop ou None, eventos). Atualiza `st` (estado guardado da loja).

    Na primeira leitura só guarda o que existe, sem avisar (senão seria tudo "novo").
    """
    data = get_json(f"{store['url']}/products.json?limit=250")
    if st.get("url") != store["url"]:  # mudou a loja (ex.: BAPE global -> UE): começa do zero, sem avisar
        st.clear()
        st["url"] = store["url"]
    prods = data.get("products", [])
    prev_ids = set(st.get("ids", []))
    first = not prev_ids
    new = [p for p in prods if p.get("id") not in prev_ids]
    st["ids"] = sorted(prev_ids | {p["id"] for p in prods if "id" in p})[-3000:]

    brand = store["brand"]
    events, drop = [], None
    mapped = [map_product(p, store) for p in new]
    if not first and mapped:
        events.append(dict(type="store_new", brand=brand, count=len(mapped), products=mapped[:3], url=store["url"]))
        if len(mapped) >= 2:  # várias peças ao mesmo tempo = drop a acontecer agora
            d = now.date().isoformat()
            drop = dict(id=f"{brand}-{d}", brand=brand, name="Peças novas na loja", date=d, time=now.strftime("%H:%M"),
                        status="confirmado", method=BRANDS[brand]["method"], image=mapped[0]["image"],
                        products=[{k: v for k, v in m.items() if k != "handle"} for m in mapped[:30]],
                        sources=[dict(name=f"Loja {BRANDS[brand]['name']}", url=store["url"])], origin="shopify")

    # restocks das peças que estás a seguir
    by_handle = {p.get("handle"): p for p in prods}
    prev_watch, now_watch = st.get("watch", {}), {}
    for h in watch_handles:
        p = by_handle.get(h)
        if not p:
            continue
        m = map_product(p, store)
        now_watch[h] = m["available"]
        if prev_watch.get(h) is False and m["available"]:
            events.append(dict(type="restock", brand=brand, product=m))
    st["watch"] = now_watch
    return drop, events
