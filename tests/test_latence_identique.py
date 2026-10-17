"""L'instrumentation ne change rien de visible : mêmes octets, mêmes statuts, mêmes en-têtes, avec ou sans elle.

Les mêmes scénarios (flux, cache, coupure, panne du fournisseur, secours, erreur, JSON, photos, limite de débit,
voix) passent deux fois par la vraie application avec un faux fournisseur : une fois avec la mesure, une fois avec un
chronomètre inerte qui n'écrit rien et ne mesure rien. Les deux sorties doivent être identiques octet pour octet.
Les deux seules sources de hasard de la réponse (date de la signature de partage, identifiant d'une action) sont figées.
"""

import contextlib
from types import SimpleNamespace

import pytest

import latence_harness as h
from latence_harness import completed, delta, failed, full, incomplete, post_chat, snapshot

TEXT = "Pour aller de Dakar à Saint-Louis, prends un car depuis la gare routière de Pompiers, c'est le plus simple et le moins cher."
STREAM = [delta("Pour aller de Dakar à Saint-Louis, "), delta("prends un car depuis la gare routière de Pompiers, "), delta("c'est le plus simple et le moins cher."), completed(TEXT)]


class Inert:
    """Même interface que LatencyTrace, sans aucun effet : sert de référence « sans instrumentation »."""

    def __init__(self, route, **kwargs):
        pass

    def run(self, app, handler):
        return app.make_response(handler(self))

    def stage(self, name):
        return contextlib.nullcontext()

    def begin(self, name):
        pass

    def end(self, name):
        pass

    def first_word(self):
        pass

    def first_sound(self):
        pass

    def ok(self):
        pass


@pytest.fixture
def lines():
    handler = h.capture_lines()
    yield handler.lines
    h.release_lines(handler)


def scenarios(monkeypatch):
    """Toutes les sorties visibles, par nom de scénario."""
    h.app_module.ANSWER_CACHE._memory.clear()
    out = {}

    def provider(**kwargs):
        return h.install_provider(monkeypatch, **kwargs)

    provider(events=STREAM)
    out["flux"] = snapshot(post_chat("Comment aller de Dakar à Saint-Louis en transport ?"))
    out["flux_depuis_le_cache"] = snapshot(post_chat("Comment aller de Dakar à Saint-Louis en transport ?"))
    out["json_depuis_le_cache"] = snapshot(post_chat("Comment aller de Dakar à Saint-Louis en transport ?", json_mode=True))
    provider(events=[delta(TEXT), incomplete(TEXT)])
    out["flux_coupe_par_la_limite"] = snapshot(post_chat("Quel car prendre pour aller de Dakar à Thiès ?"))
    provider(error="fournisseur en panne")
    out["flux_secours"] = snapshot(post_chat("Que visiter à Gorée ?"))
    out["json_secours"] = snapshot(post_chat("Que visiter à Saly ?", json_mode=True))
    provider(events=[failed()])
    out["flux_response_failed"] = snapshot(post_chat("Quelle est la meilleure saison pour Lompoul ?"))
    provider(events=[], full_reply=full("Réponse complète sans flux, donnée par le second appel."))
    out["flux_vide_puis_sans_flux"] = snapshot(post_chat("Où manger un thiéboudienne à Dakar ?"))
    provider(events=[], full_reply=full(""))
    out["flux_rien_du_tout"] = snapshot(post_chat("Une question sans réponse du modèle ?"))
    provider(events=STREAM, full_reply=full("Réponse JSON normale du fournisseur, assez longue pour être mise en cache et rejouée."))
    out["json"] = snapshot(post_chat("Quelle monnaie utilise-t-on au Sénégal ?", json_mode=True))
    out["message_vide"] = snapshot(post_chat("   "))
    out["photos"] = snapshot(post_chat("Montre-moi des photos de la Pointe des Almadies"))
    ip = h.next_ip()
    out["limite_de_debit"] = [snapshot(post_chat("Salut", ip=ip)) for _ in range(h.app_module.RATE_LIMIT + 2)]
    out["stt"] = snapshot(h.post_stt(text="bonjour Teranga", monkeypatch=monkeypatch))
    out["stt_panne"] = snapshot(h.post_stt(error="stt en panne", monkeypatch=monkeypatch))
    out["stt_sans_audio"] = snapshot(h.post_stt(audio=None, monkeypatch=monkeypatch))
    out["tts"] = snapshot(h.post_tts("Bonjour **Dakar**", monkeypatch=monkeypatch))
    out["tts_panne"] = snapshot(h.post_tts("Bonjour", error="tts en panne", monkeypatch=monkeypatch))
    out["tts_vide"] = snapshot(h.post_tts("   ", monkeypatch=monkeypatch))
    out["tts_flux"] = snapshot(h.post_tts("Bonjour **Dakar**", flux=True, monkeypatch=monkeypatch))
    out["tts_flux_panne"] = snapshot(h.post_tts("Bonjour", flux=True, error="tts en panne", monkeypatch=monkeypatch))
    out["tts_flux_coupe"] = snapshot(h.post_tts("Bonjour", flux=True, cut=1, error="coupure", monkeypatch=monkeypatch))
    return out


def test_the_output_is_identical_byte_for_byte_with_and_without_the_instrumentation(monkeypatch, lines):
    from services import action_executor, shared_answers

    monkeypatch.setattr(shared_answers, "time", SimpleNamespace(time=lambda: 1_700_000_000))
    monkeypatch.setattr(action_executor, "uuid4", lambda: SimpleNamespace(hex="0" * 32))

    measured = scenarios(monkeypatch)
    lines_with = list(lines)
    del lines[:]

    import routes.chat
    import routes.stt
    import routes.tts
    from services import chat_service

    for module in (routes.chat, routes.stt, routes.tts):
        monkeypatch.setattr(module, "LatencyTrace", Inert)
    monkeypatch.setattr(chat_service, "note_model", lambda payload, name: None)
    bare = scenarios(monkeypatch)

    assert lines == []  # la référence n'écrit vraiment rien
    assert len(lines_with) >= 20  # la mesure, elle, a bien tourné pendant le premier passage
    assert measured.keys() == bare.keys()
    for name in measured:
        assert measured[name] == bare[name], name

    # Garde-fou : les scénarios couvrent bien des réponses de toute nature (sinon l'égalité ne prouverait rien).
    statuses = {snap["status"] for snap in measured.values() if isinstance(snap, dict)}
    assert {200, 400, 500, 502} <= statuses
    assert any(snap["status"] == 429 for snap in measured["limite_de_debit"])
    assert b'"degraded"' in measured["flux_secours"]["body"] and b'"done": true' in measured["flux"]["body"]
