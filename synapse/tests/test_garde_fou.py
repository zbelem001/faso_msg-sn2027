import asyncio
import enum
import sys
import types

# Synapse n'est pas installé dans l'environnement de test : on fournit les deux symboles
# que le module importe (si Synapse est installé, ce sont les vrais qui sont utilisés).
class _Codes(str, enum.Enum):
    FORBIDDEN = "M_FORBIDDEN"


for nom in ("synapse", "synapse.api", "synapse.api.errors", "synapse.module_api"):
    sys.modules.setdefault(nom, types.ModuleType(nom))
if not hasattr(sys.modules["synapse.api.errors"], "Codes"):
    sys.modules["synapse.api.errors"].Codes = _Codes
    sys.modules["synapse.module_api"].NOT_SPAM = "NOT_SPAM"
    sys.modules["synapse.module_api"].ModuleApi = object

from synapse.api.errors import Codes  # noqa: E402
from synapse.module_api import NOT_SPAM  # noqa: E402

from garde_fou import GardeFouChiffrement  # noqa: E402


class FausseApi:
    def register_spam_checker_callbacks(self, check_event_for_spam, user_may_create_room,
                                        user_may_publish_room):
        self.rappel = check_event_for_spam
        self.creation = user_may_create_room
        self.publication = user_may_publish_room


class Evenement:
    def __init__(self, type, content=None, etat=False):
        self.type = type
        self.content = content or {}
        self._etat = etat

    def is_state(self):
        return self._etat


def garde_fou():
    api = FausseApi()
    GardeFouChiffrement({}, api)
    return api


def verifier(evenement):
    return asyncio.run(garde_fou().rappel(evenement))


def creer_salon(config):
    return asyncio.run(garde_fou().creation("@awa.demo:messagerie.gov.bf", config))


def test_message_chiffre_accepte():
    assert verifier(Evenement("m.room.encrypted", {"algorithm": "m.megolm.v1.aes-sha2"})) == NOT_SPAM


def test_message_en_clair_refuse():
    assert verifier(Evenement("m.room.message", {"msgtype": "m.text", "body": "secret"})) == Codes.FORBIDDEN


def test_reaction_en_clair_refusee():
    assert verifier(Evenement("m.reaction", {"m.relates_to": {"key": "👍"}})) == Codes.FORBIDDEN


def test_suppression_sans_motif_acceptee():
    assert verifier(Evenement("m.room.redaction", {"redacts": "$abc"})) == NOT_SPAM


def test_suppression_avec_motif_refusee():
    assert verifier(Evenement("m.room.redaction", {"redacts": "$abc", "reason": "erreur"})) == Codes.FORBIDDEN


def test_salon_public_refuse():
    assert verifier(Evenement("m.room.join_rules", {"join_rule": "public"}, etat=True)) == Codes.FORBIDDEN


def test_salon_sur_invitation_accepte():
    assert verifier(Evenement("m.room.join_rules", {"join_rule": "invite"}, etat=True)) == NOT_SPAM


def test_evenement_d_etat_accepte():
    assert verifier(Evenement("m.room.member", {"membership": "join"}, etat=True)) == NOT_SPAM


def test_creation_salon_prive_acceptee():
    assert creer_salon({"preset": "private_chat", "name": "Salon"}) == NOT_SPAM
    assert creer_salon({}) == NOT_SPAM


def test_creation_salon_public_refusee():
    assert creer_salon({"preset": "public_chat"}) == Codes.FORBIDDEN
    assert creer_salon({"visibility": "public"}) == Codes.FORBIDDEN


def test_creation_avec_regle_publique_refusee():
    etat = [{"type": "m.room.join_rules", "content": {"join_rule": "public"}}]
    assert creer_salon({"preset": "private_chat", "initial_state": etat}) == Codes.FORBIDDEN


def test_publication_dans_l_annuaire_refusee():
    assert asyncio.run(garde_fou().publication("@awa.demo:messagerie.gov.bf", "!salon")) == Codes.FORBIDDEN
