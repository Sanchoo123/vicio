"""Avisos no iPhone pela app ntfy (https://ntfy.sh). Sem tópico configurado, só escreve no registo."""
import os

from .http import post_json

SERVER = os.environ.get("NTFY_SERVER", "https://ntfy.sh").rstrip("/")


def send(msgs, dry_run=False):
    """msgs: lista de dicts {title, message, click?, attach?, tags?, priority?, at?(unix)}. Devolve quantos foram."""
    topic = os.environ.get("NTFY_TOPIC", "").strip()
    sent = 0
    for m in msgs:
        payload = {"topic": topic, "title": m["title"], "message": m["message"],
                   "tags": m.get("tags", []), "priority": m.get("priority", 3)}
        if m.get("click"):
            payload["click"] = m["click"]
        if m.get("attach"):
            payload["attach"] = m["attach"]
        if m.get("at"):
            payload["delay"] = str(int(m["at"]))
        if dry_run or not topic:
            when = f" (agendado {m['at']})" if m.get("at") else ""
            print(f"[aviso{when}] {m['title']} — {m['message'].splitlines()[0] if m['message'] else ''}")
            sent += 1
            continue
        try:
            post_json(SERVER, payload)
            sent += 1
        except Exception as e:  # um aviso falhado não pode parar o robô
            print(f"[aviso falhou] {m['title']}: {e}")
    return sent
