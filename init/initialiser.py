"""Initialisation, une seule fois au démarrage de la pile.

Crée le compte de service @console-admin (administrateur Synapse) avec le secret d'enregistrement
de Synapse, puis dépose son jeton d'accès dans un volume lu par la console. Seul ce conteneur lit
le secret d'enregistrement, et il s'arrête ensuite. Relancé, il ne fait rien si le jeton est valide.
"""
import hashlib
import hmac
import os
import secrets
import sys
import time
from pathlib import Path

import httpx

SYNAPSE_URL = os.environ.get("SYNAPSE_URL", "http://synapse:8008")
SECRET = Path(os.environ.get("SYNAPSE_REGISTRATION_SECRET_FILE", "/synapse-data/registration_shared_secret"))
JETON = Path(os.environ.get("SYNAPSE_ADMIN_TOKEN_FILE", "/run/console/synapse_admin_token"))
COMPTE = "console-admin"


def attendre_synapse(http: httpx.Client) -> None:
    for _ in range(60):
        try:
            if http.get(f"{SYNAPSE_URL}/health").status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(2)
    sys.exit("Synapse ne répond pas.")


def jeton_valide(http: httpx.Client, jeton: str) -> bool:
    r = http.get(f"{SYNAPSE_URL}/_matrix/client/v3/account/whoami", headers={"Authorization": f"Bearer {jeton}"})
    return r.status_code == 200


def creer_compte_service(http: httpx.Client) -> str:
    # API d'enregistrement par secret partagé de Synapse : le code HMAC-SHA1, calculé avec la
    # bibliothèque standard, prouve que l'on connaît le secret (format fixé par la documentation).
    secret = SECRET.read_text().strip()
    nonce = http.get(f"{SYNAPSE_URL}/_synapse/admin/v1/register").json()["nonce"]
    mot_de_passe = secrets.token_urlsafe(32)  # jamais utilisé : la connexion par mot de passe est désactivée
    message = b"\x00".join(p.encode() for p in (nonce, COMPTE, mot_de_passe, "admin"))
    code = hmac.new(secret.encode(), message, hashlib.sha1).hexdigest()
    r = http.post(f"{SYNAPSE_URL}/_synapse/admin/v1/register",
                  json={"nonce": nonce, "username": COMPTE, "password": mot_de_passe, "admin": True, "mac": code})
    if r.status_code == 400 and r.json().get("errcode") == "M_USER_IN_USE":
        sys.exit(f"@{COMPTE} existe déjà mais son jeton est perdu : réinitialiser la pile (docker compose down -v).")
    r.raise_for_status()
    return r.json()["access_token"]


def main() -> None:
    with httpx.Client(timeout=10) as http:
        attendre_synapse(http)
        if JETON.exists() and jeton_valide(http, JETON.read_text().strip()):
            print("Jeton de la console déjà valide : rien à faire.")
            return
        JETON.write_text(creer_compte_service(http))
        JETON.chmod(0o600)
        print(f"Compte de service @{COMPTE} créé, jeton déposé pour la console.")


if __name__ == "__main__":
    main()
