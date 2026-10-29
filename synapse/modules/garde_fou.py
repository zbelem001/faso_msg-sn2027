"""Garde-fou de la messagerie : Synapse refuse tout contenu qui n'est pas chiffré.

Module chargé par Synapse via son API de modules officielle (rappel check_event_for_spam).
Il ne fait aucune cryptographie : il lit seulement le type de chaque événement envoyé par
un client. Même un client modifié ne peut donc pas faire stocker un message en clair.
"""
from synapse.api.errors import Codes
from synapse.module_api import NOT_SPAM, ModuleApi

# Événements hors état autorisés : le contenu chiffré et les suppressions.
TYPES_AUTORISES = {"m.room.encrypted", "m.room.redaction"}


class GardeFouChiffrement:
    def __init__(self, config: dict, api: ModuleApi):
        api.register_spam_checker_callbacks(
            check_event_for_spam=self.verifier,
            user_may_create_room=self.verifier_creation_salon,
            user_may_publish_room=self.refuser_publication,
        )

    async def verifier_creation_salon(self, user_id: str, room_config: dict):
        # À la création, Synapse écrit l'état initial du salon sans passer par verifier() :
        # on refuse donc ici les salons publics (préréglage public ou règle d'entrée publique).
        preset = room_config.get("preset") or (
            "public_chat" if room_config.get("visibility") == "public" else "private_chat")
        regle_publique = any(
            etat.get("type") == "m.room.join_rules" and etat.get("content", {}).get("join_rule") == "public"
            for etat in room_config.get("initial_state", []))
        return Codes.FORBIDDEN if preset == "public_chat" or regle_publique else NOT_SPAM

    async def refuser_publication(self, user_id: str, room_id: str):
        return Codes.FORBIDDEN  # pas d'annuaire public des salons

    async def verifier(self, event):
        if event.is_state():
            # Nom, sujet, membres : métadonnées visibles du serveur, documentées dans la note
            # de sécurité. Seule règle : pas de salon public, on n'entre que sur invitation.
            if event.type == "m.room.join_rules" and event.content.get("join_rule") == "public":
                return Codes.FORBIDDEN
            return NOT_SPAM
        if event.type not in TYPES_AUTORISES:
            return Codes.FORBIDDEN  # message, réaction ou fichier en clair : refusé
        if event.type == "m.room.redaction" and event.content.get("reason"):
            return Codes.FORBIDDEN  # le motif d'une suppression serait stocké en clair
        return NOT_SPAM
