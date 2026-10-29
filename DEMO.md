# Démonstration

Tous les comptes et toutes les données sont **fictifs**.

## Avant de commencer

1. Lancer la messagerie : `docker compose up -d` (environ une minute au premier démarrage).
2. Faire confiance à l'autorité de certification interne de Caddy, propre à chaque installation :
   ```bash
   docker compose cp caddy:/data/caddy/pki/authorities/local/root.crt ./autorite-locale.crt
   ```
   Puis importer `autorite-locale.crt` dans le navigateur, comme autorité de confiance pour les sites web :
   - Firefox : Paramètres > Vie privée et sécurité > Certificats > Afficher les certificats > Autorités > Importer ;
   - Chrome : `chrome://certificate-manager` > Certificats locaux > Importer.

## Adresses

| Service | Adresse |
|---|---|
| Messagerie (Element) | https://element.localhost |
| Identité (Keycloak, administration technique) | https://auth.localhost/admin (identifiant `admin`, mot de passe `admin-demo`) |

## Comptes de démonstration

Mot de passe commun : **`Agent-Demo-2026`**

Le second facteur est obligatoire. Le plus simple : **scanner le QR code du compte** avec une application d'authentification (Aegis, FreeOTP, ou toute application compatible RFC 6238). En saisie manuelle : type « basé sur le temps », 6 chiffres, 30 secondes, SHA-1, et le secret ci-dessous. L'heure du téléphone doit être exacte (réglage automatique).

| Identifiant | Nom | Ministère, fonction | Groupes | Secret TOTP (fictif) | QR code |
|---|---|---|---|---|---|
| `awa.demo` | Awa Sawadogo | Santé, directrice des ressources humaines | `agents` | `KVTG6MKMKZWEM3ZQONBUORRYIY2TO43L` | [awa.demo.png](docs/totp-demo/awa.demo.png) |
| `issa.demo` | Issa Traoré | Économie et Finances, chef du service du budget | `agents` | `KEZWI42IG5WXKZ22PIYGOULZJRWUYZDD` | [issa.demo.png](docs/totp-demo/issa.demo.png) |
| `fatou.demo` | Fatou Ouédraogo | Éducation nationale, chargée d'études | `agents` | `JR4DK4KZOV2XORSBLFNGKWSWJ5UW4VSK` | [fatou.demo.png](docs/totp-demo/fatou.demo.png) |
| `admin.demo` | Salif Zongo | Transition digitale, administrateur de la messagerie | `agents`, `admin-messagerie` | `KV3GYMLQMZQUENLKHAYTIURVNE4HITRZ` | [admin.demo.png](docs/totp-demo/admin.demo.png) |
| `externe.demo` | Visiteur Externe | Aucun | aucun | `IJXXQULYHFGGG5CTIVUHCZZZOZZVSQLP` | [externe.demo.png](docs/totp-demo/externe.demo.png) |

Le compte `admin` (mot de passe `admin-demo`) sert uniquement à la console technique de Keycloak : il ne permet pas de se connecter à la messagerie.

`externe.demo` existe dans l'annuaire mais n'est pas enrôlé comme agent : la messagerie le refuse (épreuve « Intrus »).

## Scénario : échange chiffré

1. Dans un premier navigateur, ouvrir https://element.localhost, cliquer sur « Compte agent de l'État », se connecter avec `awa.demo` (mot de passe puis code TOTP).
2. Dans une fenêtre privée ou un second navigateur, faire de même avec `issa.demo`.
3. Awa crée un salon (chiffré par défaut), invite `@issa.demo:messagerie.gov.bf` et envoie un message.
4. Vérifier que la base ne contient que du contenu chiffré :
   ```bash
   docker compose exec postgres psql -U synapse -d synapse -c \
     "SELECT e.type, j.json FROM events e JOIN event_json j USING (event_id)
      WHERE e.type IN ('m.room.message', 'm.room.encrypted')
      ORDER BY e.stream_ordering DESC LIMIT 5;"
   ```
   On ne doit voir que des événements `m.room.encrypted`, avec un champ `ciphertext` illisible.
