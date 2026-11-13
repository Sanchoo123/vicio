"""Notificações na própria app Vício (Web Push, iPhone com iOS 16.4+ e a app no ecrã principal).

A app subscreve as notificações e guarda a subscrição em data/me.json, cifrada com a chave pública
PUSH_BOX_PUB (está no index.html): o repositório é público e só o robô, com o segredo PUSH_BOX_KEY,
a consegue abrir. Os envios são assinados com o segredo VAPID_PRIVATE_KEY.

Precisa do pacote pywebpush (o workflow instala-o). Sem segredos ou sem subscrições, não faz nada."""
import base64
import json
import os
import time

CONTACT = "https://sanchoo123.github.io"  # a Apple pede um contacto (URL ou mailto) em cada envio
BOX_INFO = b"vicio-push-v1"
BOX_SALT = b"vicio"


def _b64d(s):
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def open_box(box, priv_b64):
    """Abre a subscrição cifrada pela app (ECDH P-256 + HKDF-SHA256 + AES-GCM)."""
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.hkdf import HKDF

    priv = ec.derive_private_key(int.from_bytes(_b64d(priv_b64), "big"), ec.SECP256R1())
    peer = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), _b64d(box["epk"]))
    key = HKDF(algorithm=hashes.SHA256(), length=32, salt=BOX_SALT, info=BOX_INFO).derive(priv.exchange(ec.ECDH(), peer))
    return json.loads(AESGCM(key).decrypt(_b64d(box["iv"]), _b64d(box["ct"]), None))


def load_subs(me):
    """Subscrições guardadas pela app -> [{id, sub}]. Vazio se faltar o segredo."""
    key = os.environ.get("PUSH_BOX_KEY", "").strip()
    out = []
    if not key:
        return out
    for p in me.get("push") or []:
        try:
            out.append(dict(id=p["id"], sub=open_box(p["box"], key)))
        except Exception as e:  # subscrição estragada: ignora-se, a app volta a pedir
            print(f"[push] subscrição {p.get('id')} ilegível: {type(e).__name__}")
    return out


def payload(m):
    return json.dumps(dict(title=m["title"], body=m.get("message", ""), url=m.get("open") or m.get("click") or "./",
                           tag=m.get("tag")), ensure_ascii=False)


def send(msgs, subs, dry_run=False):
    """Manda já cada mensagem para cada aparelho. Devolve (enviadas, ids de subscrições mortas)."""
    sent, dead = 0, set()
    if not msgs or not subs:
        return sent, dead
    if dry_run:
        for m in msgs:
            print(f"[push] {m['title']} — {m.get('message', '').splitlines()[0] if m.get('message') else ''}")
        return len(msgs), dead
    from py_vapid import Vapid
    from pywebpush import WebPushException, webpush

    vapid = Vapid.from_raw(os.environ["VAPID_PRIVATE_KEY"].strip().encode())
    for m in msgs:
        ok = False
        for s in subs:
            if s["id"] in dead:
                continue
            try:
                # claims novas em cada envio (o pywebpush acrescenta-lhes o "aud" do serviço de cada aparelho);
                # validade curta: a Apple recusa tokens com mais de 1 hora
                webpush(s["sub"], payload(m), vapid_private_key=vapid, vapid_claims={"sub": CONTACT, "exp": int(time.time()) + 3000},
                        ttl=6 * 3600, headers={"Urgency": "high" if m.get("priority", 3) >= 4 else "normal"}, timeout=15)
                ok = True
            except WebPushException as e:
                code = getattr(e.response, "status_code", None)
                if code in (404, 410):  # o iPhone deixou de aceitar (app apagada ou notificações desligadas)
                    dead.add(s["id"])
                print(f"[push falhou] {m['title']}: HTTP {code}")
            except Exception as e:  # um aviso falhado não pode parar o robô
                print(f"[push falhou] {m['title']}: {type(e).__name__}")
        sent += ok
    return sent, dead
