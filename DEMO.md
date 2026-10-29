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
| Console d'administration (révocation, journal d'audit) | https://admin.localhost (compte `admin.demo`) |
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

Les noms et sujets de salons ne sont pas chiffrés dans Matrix (métadonnée documentée) : utiliser des noms neutres.

## Scénario : révocation pendant une conversation de groupe

1. Awa, Issa et Fatou sont dans un même salon et échangent des messages.
2. Dans un autre navigateur, ouvrir https://admin.localhost et se connecter avec `admin.demo`.
3. Cliquer sur « Révoquer » sur la ligne de Fatou, saisir un motif, confirmer.
4. Le rapport s'affiche : toutes les étapes doivent être cochées, en une à deux secondes.
5. Fatou est déconnectée de la messagerie et ne peut plus se reconnecter (« Compte désactivé »). Elle n'est plus membre du salon : Awa et Issa continuent sans elle, et les nouveaux messages sont chiffrés avec une nouvelle clé de groupe qu'elle ne reçoit pas.
6. L'onglet « Journal d'audit » garde la trace de la révocation (qui, quand, quel agent, motif).

## Scénario : intrus

| Tentative | Résultat attendu |
|---|---|
| Connexion avec `externe.demo` (compte non enrôlé comme agent) | Refusée par la messagerie |
| Connexion d'un agent révoqué | « Compte désactivé » |
| Mot de passe correct, code TOTP faux | Refusée par Keycloak |
| Agent simple (`issa.demo`) sur https://admin.localhost | Refusé (403) |
| Inscription directe sur le serveur Matrix | `curl -k -X POST https://matrix.localhost/_matrix/client/v3/register -d '{}'` : « Registration has been disabled » |
| Message en clair envoyé directement à l'API | Refusé (403) par le garde-fou du serveur |
| Création d'un salon public | Refusée (403) par le garde-fou |

## Tests automatisés

```bash
pip install -r console-admin/requirements-tests.txt
pytest
```

Ils couvrent la révocation (ordre des étapes, agent inconnu), la vérification des jetons de la console (signature forgée, jeton modifié, expiré, autre émetteur, autre audience, agent sans droit) et le garde-fou du serveur.
