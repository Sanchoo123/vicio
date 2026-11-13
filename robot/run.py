"""Uma ronda do robô: lê as fontes, junta os drops, decide os avisos e grava os ficheiros em data/.

Uso:  python -m robot.run            (manda avisos se NTFY_TOPIC estiver definido)
      python -m robot.run --dry-run  (só mostra o que faria)
"""
import json
import sys
import traceback
from datetime import date, datetime, timedelta
from pathlib import Path

from . import ics, notify
from .config import BRANDS, FEEDS, GNEWS_EVERY, NIKE_EVERY, KEEP_PAST_DAYS, MAX_PUSH_PER_RUN, NTFY_MAX_DELAY_DAYS, STORES, TZ
from .http import Blocked, get
from .sources import gnews, manual, nike, password, patterns, rss, shopify

DATA = Path(__file__).resolve().parent.parent / "data"
RANK = {"pattern": 0, "rss": 1, "shopify": 2, "nike": 2, "manual": 3}
WD = ["SEG", "TER", "QUA", "QUI", "SEX", "SÁB", "DOM"]
MO = ["JAN", "FEV", "MAR", "ABR", "MAI", "JUN", "JUL", "AGO", "SET", "OUT", "NOV", "DEZ"]


# ---------- ficheiros ----------
def load(name, default):
    p = DATA / name
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default


def write(name, content):
    """Só escreve se mudou (assim o GitHub não faz commits vazios)."""
    p = DATA / name
    text = content if isinstance(content, str) else json.dumps(content, ensure_ascii=False, indent=1, sort_keys=True) + "\n"
    if p.exists() and p.read_text(encoding="utf-8") == text:
        return False
    p.write_text(text, encoding="utf-8", newline="")
    return True


# ---------- juntar drops ----------
def merge(cands):
    out = {}
    for c in sorted(cands, key=lambda c: RANK[c["origin"]]):
        cur = out.get(c["id"])
        if not cur:
            out[c["id"]] = dict(c)
            continue
        srcs = {s["url"]: s for s in cur.get("sources", []) + c.get("sources", [])}
        cur.update({k: v for k, v in c.items() if v not in (None, [], "")})
        cur["sources"] = list(srcs.values())
    return sorted(out.values(), key=lambda d: (d["date"], d.get("time") or "99:99", d["id"]))


def attach_droplists(drops, news):
    """Notícia de 'drop list' da Supreme/Palace -> confirma o drop previsto dessa semana."""
    for n in news:
        if not n.get("droplist") or not n.get("published"):
            continue
        pub = date.fromisoformat(n["published"][:10])
        for d in drops:
            dd = date.fromisoformat(d["date"])
            if d["brand"] == n["brand"] and pub <= dd <= pub + timedelta(days=4):
                if d["status"] == "previsto":
                    d["status"] = "confirmado"
                d["image"] = d.get("image") or n.get("image")
                d["droplist"] = n["url"]
                if all(s["url"] != n["url"] for s in d["sources"]):
                    d["sources"].append(dict(name=n["source"], url=n["url"]))
                break


# ---------- textos ----------
def day_txt(iso):
    d = date.fromisoformat(iso)
    return f"{WD[d.weekday()]} {d.day} {MO[d.month - 1]}"


def when_txt(d):
    return f"{day_txt(d['date'])} · {d['time'] + ' Lisboa' if d.get('time') else 'hora por confirmar'}"


def drop_ts(d):
    if not d.get("time"):
        return None
    y, m, dd = map(int, d["date"].split("-"))
    h, mi = map(int, d["time"].split(":"))
    return datetime(y, m, dd, h, mi, tzinfo=TZ)


# ---------- avisos ----------
def level(me, brand):
    return me.get("avisos_por_marca", {}).get(brand, "drops")


def allowed(me, kind, brand, going):
    lv = level(me, brand)
    if lv == "nada":
        return False
    if kind in ("reminder", "restock", "store_open") or (going and kind in ("changed", "revealed", "confirmed")):
        return True
    if lv == "meus":
        return False
    if kind == "news":
        return lv == "tudo"
    return True


def build_messages(events, me):
    going = me.get("vou_entrar", {})
    msgs = []
    for e in events:
        k, d = e["type"], e.get("drop")
        brand = e.get("brand") or (d and d["brand"]) or (e.get("item") or {}).get("brand")
        bn = BRANDS.get(brand, {}).get("name", brand or "?")
        if not allowed(me, k, brand, bool(d and d["id"] in going)):
            continue
        click = d and d.get("sources") and d["sources"][-1]["url"]
        if k == "new_drop":
            msgs.append(dict(title=f"Novo drop: {bn} · {day_txt(d['date'])}", message=f"{d['name']}\n{when_txt(d)}",
                             click=click, attach=d.get("image"), tags=["calendar"]))
        elif k == "changed":
            msgs.append(dict(title=f"Mudou a data: {bn}", message=f"{d['name']}\nAgora: {when_txt(d)}\nAntes: {e['before']}",
                             click=click, tags=["warning"], priority=4))
        elif k == "confirmed":
            msgs.append(dict(title=f"Confirmado: {bn} · {day_txt(d['date'])}", message=f"{d['name']}\n{when_txt(d)}",
                             click=click, attach=d.get("image"), tags=["white_check_mark"]))
        elif k == "revealed":
            msgs.append(dict(title=f"Lista revelada: {bn}", message=f"{d['name']} · {when_txt(d)}\nJá dá para ver as peças.",
                             click=d.get("droplist") or click, attach=d.get("image"), tags=["eyes"], priority=4))
        elif k == "news":
            n = e["item"]
            msgs.append(dict(title=f"{bn}: novidade", message=n["title"], click=n["url"], attach=n.get("image"), tags=["newspaper"]))
        elif k == "store_new":
            names = ", ".join(p["name"] for p in e["products"])
            msgs.append(dict(title=f"{bn}: {e['count']} {'peça nova' if e['count'] == 1 else 'peças novas'} na loja",
                             message=names, click=e["url"], attach=e["products"][0].get("image"), tags=["fire"], priority=4))
        elif k == "store_open":
            msgs.append(dict(title=f"{bn}: a loja abriu!", message="A página de palavra-passe saiu. O drop deve estar a decorrer, corre!",
                             click=e["url"], tags=["rotating_light"], priority=5))
        elif k == "restock":
            p = e["product"]
            msgs.append(dict(title=f"Restock: {p['name']}", message=f"{bn} voltou a ter stock. Corre!", click=p["url"],
                             attach=p.get("image"), tags=["rotating_light"], priority=5))
    if len(msgs) > MAX_PUSH_PER_RUN:
        extra = len(msgs) - (MAX_PUSH_PER_RUN - 1)
        msgs = msgs[:MAX_PUSH_PER_RUN - 1] + [dict(title=f"E mais {extra} novidades", message="Abre o Vício para ver tudo.", tags=["calendar"])]
    return msgs


def reminders(drops, me, state, now):
    """Agenda no ntfy os lembretes (1 h antes e 10 min antes) dos drops onde vais entrar."""
    going, done, msgs = me.get("vou_entrar", {}), set(state.get("reminders", [])), []
    for d in drops:
        if d["id"] not in going or level(me, d["brand"]) == "nada":
            continue
        ts = drop_ts(d)
        if not ts or ts <= now or ts - now > timedelta(days=NTFY_MAX_DELAY_DAYS):
            continue
        bn = BRANDS[d["brand"]]["name"]
        pecas = (going[d["id"]] or {}).get("pecas", []) if isinstance(going[d["id"]], dict) else []
        lista = ("\nNa mira: " + ", ".join(f"{i + 1}. {p}" for i, p in enumerate(pecas))) if pecas else ""
        for mins, title, prio in ((60, f"Daqui a 1 hora: {bn}", 4), (10, f"10 minutos: faz login na {bn}", 5)):
            key = f"{d['id']}|{d['date']}|{d['time']}|{mins}"
            at = ts - timedelta(minutes=mins)
            if key in done or at <= now:
                continue
            msgs.append(dict(title=title, message=f"{d['name']} às {d['time']}{lista}", at=at.timestamp(),
                             click=d["sources"][-1]["url"] if d.get("sources") else None, tags=["alarm_clock"], priority=prio))
            done.add(key)
    state["reminders"] = sorted(done)[-300:]
    return msgs


def weekly_summary(drops, me, state, now):
    """Domingo à noite: a tua semana de drops."""
    week = f"{now.isocalendar().year}-W{now.isocalendar().week:02d}"
    if now.weekday() != 6 or now.hour < 19 or state.get("summary_week") == week:
        return []
    state["summary_week"] = week
    start, end = now.date() + timedelta(days=1), now.date() + timedelta(days=7)
    going = me.get("vou_entrar", {})
    sel = [d for d in drops if start <= date.fromisoformat(d["date"]) <= end and level(me, d["brand"]) != "nada"]
    if not sel:
        return [dict(title="A tua semana de drops", message="Sem drops conhecidos esta semana.", tags=["calendar"])]
    lines = [f"{'✓ ' if d['id'] in going else ''}{day_txt(d['date'])} {d.get('time') or ''} · {BRANDS[d['brand']]['name']} · {d['name']}"
             + (" (previsto)" if d["status"] == "previsto" else "") for d in sel]
    n_in = sum(1 for d in sel if d["id"] in going)
    return [dict(title=f"A tua semana: {len(sel)} drops, entras em {n_in}", message="\n".join(lines), tags=["calendar"])]


# ---------- ronda ----------
def run(now=None, dry_run=False):
    now = now or datetime.now(TZ)
    today = now.date()
    state = load("state.json", {})
    first_run = not state
    me = load("me.json", {})
    status = load("status.json", {}).get("sources", {})  # lojas não lidas nesta ronda mantêm o último estado
    cands, events, news = [], [], []

    # 1. ritmo habitual
    cands += patterns.expected(now)

    # 2. notícias
    for f in FEEDS:
        try:
            items = rss.parse_feed(get(f["url"]), f["name"], today)
            news += items
            cands += [rss.to_drop(i) for i in items if i.get("date")]
            status[f["name"]] = dict(ok=True)
        except Blocked as e:
            status[f["name"]] = dict(ok=False, msg=str(e))
        except Exception as e:
            status[f["name"]] = dict(ok=False, msg=f"erro: {type(e).__name__}")

    slot = (now.hour * 60 + now.minute) // 30

    # 2b. Google Notícias, de hora a hora (nas meias-horas em que a BAPE não é lida)
    if first_run or not state.get("gnews_ok") or slot % max(1, GNEWS_EVERY // 30) == 1:
        items, errs = gnews.fetch(today)
        news += items
        cands += [rss.to_drop(i) for i in items if i.get("date")]
        if items or not errs:
            status["Google Notícias"] = dict(ok=True, msg="; ".join(errs)) if errs else dict(ok=True)
        else:
            status["Google Notícias"] = dict(ok=False, msg="; ".join(errs)[:200])
        state["gnews_ok"] = True

    # 2c. calendário oficial SNKRS Portugal, de hora a hora
    nike_ok, nike_read = state.get("nike_ok", False), False
    if first_run or not nike_ok or slot % max(1, NIKE_EVERY // 30) == 0:
        try:
            cands += nike.fetch()
            status["Nike SNKRS Portugal"] = dict(ok=True)
            nike_ok = nike_read = True
        except Blocked as e:
            status["Nike SNKRS Portugal"] = dict(ok=False, msg=str(e))
            nike_ok = False
        except Exception as e:
            status["Nike SNKRS Portugal"] = dict(ok=False, msg=f"erro: {type(e).__name__}")
            nike_ok = False
        state["nike_ok"] = nike_ok
    if nike_ok:
        # com o calendário oficial, as notícias americanas da Nike (horas dos EUA, pares que podem nem sair cá)
        # ficam só como notícia; as colaborações com as outras marcas continuam a contar
        cands = [c for c in cands if not (c["brand"] == "nike" and c["origin"] == "rss")]

    # 3. lojas com catálogo público
    watch = me.get("seguir_restock", [])
    retired = set(state.get("retired", []))
    for s in STORES:
        label = f"Loja {BRANDS[s['brand']]['name']}"
        if not first_run and slot % max(1, s["every"] // 30):
            continue  # ainda não é altura de voltar a esta loja
        st = state.setdefault("stores", {}).setdefault(s["brand"], {})
        try:
            handles = [w["handle"] for w in watch if w.get("loja") == s["brand"]]
            if s.get("password"):
                drop, ev, open_ = password.check(s, st, now, BRANDS[s["brand"]]["name"])
                if drop:
                    old = st.get("announced")
                    if old not in (None, drop["id"]) and old[-10:] >= today.isoformat():
                        retired.add(old)  # a marca mudou a data anunciada
                    st["announced"] = drop["id"]
                    cands.append(drop)
                events += ev
                if not open_:
                    status[label] = dict(ok=True, msg="fechada com palavra-passe" + (f" · anuncia drop a {day_txt(drop['date'])}" if drop else ""))
                    continue
            drop, ev = shopify.check_store(s, st, handles, now)
            if drop:
                cands.append(drop)
            events += ev
            status[label] = dict(ok=True)
        except Blocked as e:
            status[label] = dict(ok=False, msg=str(e))
        except Exception as e:
            status[label] = dict(ok=False, msg=f"erro: {type(e).__name__}")

    # 4. à mão
    man, errs = manual.load_manual(load("manual.json", {}))
    cands += man
    status["Drops à mão"] = dict(ok=not errs, msg="; ".join(errs)) if errs else dict(ok=True)

    # juntar e limpar
    drops = [d for d in merge(cands) if date.fromisoformat(d["date"]) >= today - timedelta(days=KEEP_PAST_DAYS)]
    attach_droplists(drops, news)
    # drops que já tinham sido vistos e desapareceram das fontes (ex.: notícia saiu do feed) ficam guardados
    known = load("drops.json", {}).get("drops", [])
    ids = {d["id"] for d in drops}
    for d in known:
        if nike_ok and d["brand"] == "nike" and d.get("origin") == "rss":
            continue
        if d["id"] in retired:
            continue
        if d.get("origin") == "nike" and nike_read and d["date"] >= today.isoformat():
            continue  # lançamento futuro que saiu do calendário oficial (adiado ou cancelado)
        if d["id"] not in ids and d.get("origin") in ("rss", "shopify", "nike") and date.fromisoformat(d["date"]) >= today - timedelta(days=KEEP_PAST_DAYS):
            drops.append(d)
    drops.sort(key=lambda d: (d["date"], d.get("time") or "99:99", d["id"]))

    # o que mudou desde a última ronda
    seen = state.setdefault("seen", {})
    for d in drops:
        sig = dict(date=d["date"], time=d.get("time"), status=d["status"], n=len(d.get("products", [])),
                   img=bool(d.get("image")), droplist=bool(d.get("droplist")))
        prev = seen.get(d["id"])
        if prev is None:
            if (d["origin"] in ("rss", "manual", "nike") or d.get("name") == "Novo drop") and d["date"] >= today.isoformat():
                events.append(dict(type="new_drop", drop=d))
        elif (prev["date"], prev["time"]) != (sig["date"], sig["time"]):
            events.append(dict(type="changed", drop=d, before=f"{day_txt(prev['date'])} {prev['time'] or ''}".strip()))
        elif prev["status"] == "previsto" and sig["status"] != "previsto":
            events.append(dict(type="revealed" if sig["droplist"] else "confirmed", drop=d))
        elif (prev["n"] == 0 and sig["n"] > 0) or (not prev.get("droplist") and sig["droplist"]):
            events.append(dict(type="revealed", drop=d))
        seen[d["id"]] = sig
    for k in [k for k, v in seen.items() if v["date"] < (today - timedelta(days=KEEP_PAST_DAYS)).isoformat()]:
        del seen[k]

    drop_urls = {s["url"] for d in drops for s in d.get("sources", [])}
    news_seen = set(state.get("news_seen", []))
    for n in news:
        if n["id"] not in news_seen and n["url"] not in drop_urls and not n.get("quiet"):
            events.append(dict(type="news", item=n))
        news_seen.add(n["id"])
    state["news_seen"] = sorted(news_seen)[-600:]
    state["retired"] = sorted(retired)[-100:]

    # avisos
    if first_run:
        msgs = [dict(title="Robô do Vício ligado ✓", message=f"Encontrei {len(drops)} drops. A partir de agora aviso-te das novidades.",
                     tags=["white_check_mark"])]
        reminders(drops, me, state, now)  # marca como tratados sem repetir avisos antigos
    else:
        try:
            msgs = build_messages(events, me) + reminders(drops, me, state, now) + weekly_summary(drops, me, state, now)
            status.pop("Avisos", None)
        except Exception as e:  # um erro nos avisos não pode impedir que os drops sejam gravados
            traceback.print_exc()
            msgs = []
            status["Avisos"] = dict(ok=False, msg=f"erro: {type(e).__name__}: {e}"[:200])
    sent = notify.send(msgs, dry_run=dry_run)

    # gravar
    old_news = load("news.json", {}).get("news", [])
    merged_news = {n["id"]: n for n in old_news + news}
    news_out = sorted(merged_news.values(), key=lambda n: n.get("published") or "", reverse=True)[:80]
    going = me.get("vou_entrar", {})
    changed = any([
        write("drops.json", dict(drops=drops, brands={k: dict(name=b["name"], site=b["site"]) for k, b in BRANDS.items()})),
        write("news.json", dict(news=news_out)),
        write("drops.ics", ics.build([d for d in drops if level(me, d["brand"]) != "nada"], "Vício · Drops")),
        write("meus-drops.ics", ics.build([d for d in drops if d["id"] in going], "Vício · Os meus drops", alarms=True)),
    ])
    write("status.json", dict(sources=status))
    if changed:
        write("updated.json", dict(updated=now.isoformat(timespec="minutes")))
    write("state.json", state)
    print(f"{now:%Y-%m-%d %H:%M} · {len(drops)} drops · {len(news)} notícias · {len(events)} eventos · {sent} avisos")
    for k, v in status.items():
        print(f"  {'ok ' if v['ok'] else 'X  '} {k}{' — ' + v['msg'] if v.get('msg') else ''}")
    return drops, events, msgs


if __name__ == "__main__":
    run(dry_run="--dry-run" in sys.argv)
