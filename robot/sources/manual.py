"""Drops acrescentados à mão em data/manual.json (ex.: vistos no Instagram)."""
from datetime import date

from ..config import BRANDS


def load_manual(doc):
    out, errors = [], []
    for i, d in enumerate(doc.get("drops", [])):
        b = d.get("marca") or d.get("brand")
        dt = d.get("data") or d.get("date")
        if b not in BRANDS:
            errors.append(f"drop #{i + 1}: marca desconhecida '{b}'")
            continue
        try:
            date.fromisoformat(dt)
        except (TypeError, ValueError):
            errors.append(f"drop #{i + 1}: data inválida '{dt}' (usa AAAA-MM-DD)")
            continue
        prods = [dict(name=p.get("nome", p.get("name", "")), price=p.get("preco", p.get("price")),
                      currency=p.get("moeda", "EUR"), image=p.get("imagem", p.get("image")),
                      url=p.get("link", p.get("url"))) for p in d.get("pecas", d.get("products", []))]
        out.append(dict(id=d.get("id") or f"{b}-{dt}", brand=b, name=d.get("nome", d.get("name", "Drop")),
                        date=dt, time=d.get("hora", d.get("time")),
                        status=d.get("estado", d.get("status", "confirmado")),
                        method=d.get("metodo", BRANDS[b]["method"]), image=d.get("imagem"),
                        products=prods, sources=[dict(name="Adicionado à mão", url=d.get("link") or BRANDS[b]["site"])],
                        origin="manual"))
    return out, errors
