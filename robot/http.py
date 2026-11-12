"""Pedidos HTTP simples e educados: um pedido de cada vez, nome honesto, sem insistir quando bloqueiam."""
import json
import urllib.error
import urllib.request

from .config import USER_AGENT


class Blocked(Exception):
    """A fonte recusou o pedido (401/403/429). Não se tenta contornar: fica para a próxima ronda."""


def get(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        if e.code in (401, 403, 429):
            raise Blocked(f"bloqueado (HTTP {e.code})") from None
        raise


def get_json(url, timeout=20):
    return json.loads(get(url, timeout))


def post_json(url, payload, timeout=20):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, method="POST",
                                 headers={"User-Agent": USER_AGENT, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()
