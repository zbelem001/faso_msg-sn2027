#!/bin/sh
# Démarrage de Synapse :
# 1. produit /data/homeserver.yaml à partir du modèle, en y injectant les secrets partagés
#    (mot de passe de la base, secret du client OIDC) depuis l'environnement ;
# 2. au premier lancement, fait générer par Synapse sa clé de signature et son secret
#    d'enregistrement (propres à chaque installation, jamais dans le dépôt) ;
# 3. lance le démarrage standard de l'image (qui exécute Synapse sous l'utilisateur 991).
set -e

python - <<'EOF'
import os
import re
import sys

with open("/config/homeserver.yaml") as modele:
    contenu = os.path.expandvars(modele.read())

manquantes = re.findall(r"\$\{(\w+)\}", contenu)
if manquantes:
    sys.exit("Variables d'environnement manquantes : " + ", ".join(manquantes))

with open("/data/homeserver.yaml", "w") as cible:
    cible.write(contenu)
EOF

python -m synapse.app.homeserver --config-path /data/homeserver.yaml --generate-keys
chown -R 991:991 /data

exec /start.py
