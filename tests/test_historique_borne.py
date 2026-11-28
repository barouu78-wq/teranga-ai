"""Historique du chat : une liste énorme n'est pas parcourue en entier (audit du 27 novembre 2026).

Le navigateur envoie au plus MAX_HISTORY_ITEMS répliques ; une requête fabriquée pouvait en envoyer des centaines de
milliers, toutes parcourues par prepare_cut_history avant d'être réduites aux dernières.
"""

import os

os.environ.setdefault("OPENAI_API_KEY", "test-key")

import app as app_module  # noqa: E402
from services import chat_payload_service  # noqa: E402


def _payload(history, message="Bonjour"):
    with app_module.app.test_request_context("/chat", method="POST",
                                             json={"message": message, "language": "fr", "history": history}):
        return app_module.parse_chat_payload()


def test_une_liste_enorme_est_reduite_avant_d_etre_parcourue(monkeypatch):
    recu = []
    original = chat_payload_service.prepare_cut_history
    monkeypatch.setattr(chat_payload_service, "prepare_cut_history",
                        lambda history, n: recu.append(len(history)) or original(history, n))
    payload, erreur = _payload([{"role": "assistant", "content": "x"}] * 100_000)
    assert erreur is None
    assert recu and recu[0] <= app_module.MAX_HISTORY_ITEMS * 10


def test_une_conversation_normale_garde_ses_repliques():
    history = [{"role": "user", "content": "Parle-moi de Gorée"},
               {"role": "assistant", "content": "Gorée est une île au large de Dakar."},
               {"role": "user", "content": "Et pour y aller ?"}]
    payload, erreur = _payload(history, message="Et pour y aller ?")
    assert erreur is None
    assert "Gorée est une île au large de Dakar." in payload["input_text"]
