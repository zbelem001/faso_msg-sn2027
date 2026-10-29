# Messagerie souveraine de l'administration

Messagerie instantanée chiffrée de bout en bout pour les agents publics du Burkina Faso, hébergeable sur l'infrastructure de l'État et installable en une seule commande.

> Projet réalisé pour le sprint technique pré-hackathon du Hackathon 226, édition 2026 (MTDPCE / DGTD). En cours de développement.

## Concept

*À compléter.*

## Architecture

*À compléter.*

## Technologies et licences

*À compléter.*

## Niveau d'engagement open source

**Étendre et adapter**, à partir de Matrix (Synapse, Element) et de Keycloak.

## Installation

Prérequis : Docker et Docker Compose, environ 2 Go de mémoire libre.

```bash
docker compose up -d
```

Au premier démarrage, Keycloak importe l'annuaire de démonstration et Synapse génère sa clé de signature (environ une minute). La messagerie est ensuite disponible sur https://element.localhost. Les comptes fictifs et le certificat à importer dans le navigateur sont décrits dans [DEMO.md](DEMO.md).

Les secrets de `docker-compose.yml` sont des valeurs de démonstration : en production, les remplacer dans un fichier `.env` (modèle : [.env.example](.env.example)).

## Limites connues

*À compléter.*

## Licence

Ce projet est distribué sous licence [AGPL-3.0](LICENSE).
