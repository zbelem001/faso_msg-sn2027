"""Console d'administration de la messagerie : liste des agents, révocation en un clic, journal d'audit.

Elle n'est jamais exposée directement : oauth2-proxy impose la connexion Keycloak (avec second
facteur) et lui transmet le jeton d'accès de l'administrateur, dont require_admin vérifie la signature.
"""
import json
import os
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

import httpx
import jwt
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, StringConstraints

from auth import AccesRefuse, verifier_jeton
from revocation import Config, KeycloakAdmin, SynapseAdmin, revoke_agent

KEYCLOAK_URL = os.environ["KEYCLOAK_URL"]
KEYCLOAK_REALM = os.environ.get("KEYCLOAK_REALM", "administration")
KEYCLOAK_ISSUER = os.environ["KEYCLOAK_ISSUER"]
OIDC_AUDIENCE = os.environ.get("OIDC_AUDIENCE", "oauth2-proxy")
ADMIN_GROUP = os.environ.get("ADMIN_GROUP", "admin-messagerie")
AGENTS_GROUP = os.environ.get("AGENTS_GROUP", "agents")
AUDIT_DB = os.environ.get("AUDIT_DB", "/data/audit.db")
STATIC = Path(__file__).parent / "static"

app = FastAPI(title="Console d'administration", docs_url=None, redoc_url=None, openapi_url=None)

# Clés publiques de Keycloak, téléchargées par le réseau interne et mises en cache par PyJWT
_jwks = jwt.PyJWKClient(f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/certs")

with closing(sqlite3.connect(AUDIT_DB)) as base:
    base.execute("""CREATE TABLE IF NOT EXISTS revocations (
        id INTEGER PRIMARY KEY, horodatage TEXT, administrateur TEXT, agent TEXT,
        motif TEXT, succes INTEGER, rapport TEXT)""")
    base.commit()


def config() -> Config:
    """Relue à chaque requête : le jeton Synapse est déposé par le conteneur d'initialisation."""
    jeton = os.environ.get("SYNAPSE_ADMIN_TOKEN") or Path(os.environ["SYNAPSE_ADMIN_TOKEN_FILE"]).read_text().strip()
    return Config(KEYCLOAK_URL, KEYCLOAK_REALM, os.environ["KEYCLOAK_CLIENT_ID"], os.environ["KEYCLOAK_CLIENT_SECRET"],
                  os.environ["SYNAPSE_URL"], jeton, os.environ["SYNAPSE_SERVER_NAME"])


def require_admin(x_forwarded_access_token: str | None = Header(default=None)) -> dict:
    """Laisse passer uniquement un jeton Keycloak authentique d'un membre de admin-messagerie."""
    if not x_forwarded_access_token:
        raise HTTPException(401, "Connexion requise")
    try:
        cle = _jwks.get_signing_key_from_jwt(x_forwarded_access_token).key
        return verifier_jeton(x_forwarded_access_token, cle, KEYCLOAK_ISSUER, OIDC_AUDIENCE, ADMIN_GROUP)
    except jwt.PyJWTError:
        raise HTTPException(401, "Jeton invalide ou expiré")
    except AccesRefuse:
        raise HTTPException(403, "Réservé aux administrateurs de la messagerie")


Admin = Annotated[dict, Depends(require_admin)]


class Revocation(BaseModel):
    motif: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=200)]


@app.get("/")
def page():
    return FileResponse(STATIC / "index.html")


@app.get("/api/moi")
def moi(admin: Admin):
    return {"identifiant": admin.get("preferred_username"), "nom": admin.get("name")}


@app.get("/api/agents")
def agents(admin: Admin):
    with httpx.Client(timeout=10) as http:
        membres = KeycloakAdmin(config(), http).group_members(AGENTS_GROUP)
    attribut = lambda m, nom: (m.get("attributes", {}).get(nom) or [""])[0]
    return sorted(({"identifiant": m["username"],
                    "nom": f"{m.get('firstName', '')} {m.get('lastName', '')}".strip(),
                    "ministere": attribut(m, "ministere"),
                    "fonction": attribut(m, "fonction"),
                    "actif": m.get("enabled", False)} for m in membres),
                  key=lambda a: a["nom"])


@app.post("/api/agents/{username}/revoke")
def revoquer(username: str, demande: Revocation, admin: Admin):
    username = username.lower()
    if username == admin.get("preferred_username") or username.startswith("service-account-"):
        raise HTTPException(400, "Ce compte ne peut pas être révoqué depuis la console")
    cfg = config()
    with httpx.Client(timeout=10) as http:
        rapport = revoke_agent(username, KeycloakAdmin(cfg, http), SynapseAdmin(cfg, http), cfg.server_name)
    with closing(sqlite3.connect(AUDIT_DB)) as base:
        base.execute("INSERT INTO revocations (horodatage, administrateur, agent, motif, succes, rapport) "
                     "VALUES (?, ?, ?, ?, ?, ?)",
                     (datetime.now(timezone.utc).isoformat(timespec="seconds"), admin.get("preferred_username"),
                      username, demande.motif, rapport.success, json.dumps(rapport.to_dict(), ensure_ascii=False)))
        base.commit()
    return rapport.to_dict()


@app.get("/api/audit")
def audit(admin: Admin):
    with closing(sqlite3.connect(AUDIT_DB)) as base:
        base.row_factory = sqlite3.Row
        lignes = base.execute("SELECT * FROM revocations ORDER BY id DESC LIMIT 100").fetchall()
    return [{**dict(ligne), "succes": bool(ligne["succes"]), "rapport": json.loads(ligne["rapport"])}
            for ligne in lignes]
