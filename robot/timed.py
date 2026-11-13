"""Lembretes à hora certa (1 h e 10 min antes dos drops onde vais entrar).

O robô corre de 30 em 30 minutos; os lembretes que caem antes da ronda seguinte ficam num ficheiro e
este passo espera pela hora exata de cada um e manda-o. Uso: python -m robot.timed ficheiro.json"""
import json
import sys
import time

from . import webpush
from .run import load


def main(path):
    try:
        msgs = json.loads(open(path, encoding="utf-8").read() or "[]")
    except FileNotFoundError:
        msgs = []
    if not msgs:
        print("Sem lembretes para esta meia hora.")
        return
    subs = webpush.load_subs(load("me.json", {}))
    for m in sorted(msgs, key=lambda m: m["at"]):
        wait = m["at"] - time.time()
        if wait > 0:
            print(f"À espera {int(wait // 60)} min para: {m['title']}")
            time.sleep(wait)
        n, _ = webpush.send([m], subs)
        print(f"{'Enviado' if n else 'Falhou'}: {m['title']}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "timed.json")
