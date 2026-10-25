"""Recherche web : le chat dit qu'il cherche, au lieu de trois points muets.

Mesure de production (journaux Render, 18 octobre 2026) : une question avec recherche web a attendu 16 s avant son
premier mot (`premier_mot_ms=16155.5 web=oui`), avec seulement trois points animés à l'écran. Quand le modèle lance
vraiment une recherche (événements `response.web_search_call.*` du flux), la route envoie une fois `{"st": "web"}`
avant le texte ; la page affiche alors « Je cherche des informations à jour… » sous les points. Rien n'est dit si le
modèle ne cherche pas : l'outil proposé ne suffit pas.
"""

import json
import os
import re
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.pop("ANTHROPIC_API_KEY", None)

import pytest  # noqa: E402

import app as app_module  # noqa: E402

B = "https://teranga-ai.fr"
HOME_JS = (Path(__file__).resolve().parents[1] / "static" / "home.js").read_text(encoding="utf-8")
LAST_IP = [0]


def _event(kind, **fields):
    return SimpleNamespace(type=kind, **fields)


def _delta(text):
    return _event("response.output_text.delta", delta=text)


def _completed(text):
    return _event("response.completed", response=SimpleNamespace(status="completed", incomplete_details=None,
                                                                   output_text=text, output=[]))


@pytest.fixture
def provider(monkeypatch):
    def install(stream_events):
        def create(**kwargs):
            assert kwargs.get("stream"), "le flux est attendu"
            return iter(stream_events)

        monkeypatch.setattr(app_module.client.responses, "create", create)

    return install


def _events(message="Quelles sont les dernières nouvelles sur le TER de Dakar ?"):
    LAST_IP[0] += 1
    client = app_module.app.test_client()
    token = client.get("/csrf", base_url=B).get_json()["token"]
    client.set_cookie("teranga_csrf", token, domain="teranga-ai.fr")
    response = client.post(
        "/chat",
        json={"message": message, "history": [{"role": "user", "content": message}], "language": "fr"},
        headers={"X-CSRF-Token": token, "Origin": B},
        base_url=B,
        environ_base={"REMOTE_ADDR": f"198.51.100.{180 + LAST_IP[0]}"},
    )
    return [json.loads(line) for line in response.get_data(as_text=True).splitlines() if line.strip()]


def test_une_recherche_web_est_annoncee_une_fois_avant_le_texte(provider):
    texte = "Selon les sources consultées, le TER circule normalement cette semaine."
    provider([
        _event("response.created"),
        _event("response.web_search_call.in_progress"),
        _event("response.web_search_call.searching"),
        _event("response.web_search_call.completed"),
        _delta(texte),
        _completed(texte),
    ])
    events = _events()
    statuts = [i for i, e in enumerate(events) if "st" in e]
    assert [events[i] for i in statuts] == [{"st": "web"}]
    premier_texte = next(i for i, e in enumerate(events) if "d" in e)
    assert statuts[0] < premier_texte
    assert "".join(e.get("d", "") for e in events) == texte


def test_sans_recherche_rien_n_est_annonce(provider):
    texte = "Le thiéboudienne est le plat national du Sénégal."
    provider([_event("response.created"), _delta(texte), _completed(texte)])
    assert not any("st" in e for e in _events("Parle-moi du thiéboudienne et de son histoire"))


class _FluxClaude:
    """Flux du SDK Anthropic : événements `content_block_start` / `content_block_delta`, comme `client.beta.messages.stream`."""

    def __init__(self, blocs, texte):
        self.evenements = []
        for bloc in blocs:
            self.evenements.append(_event("content_block_start", content_block=bloc))
        self.evenements.append(_event("content_block_start", content_block=SimpleNamespace(type="text", text="")))
        self.evenements.append(_event("content_block_delta", delta=SimpleNamespace(type="text_delta", text=texte)))
        self.message = SimpleNamespace(stop_reason="end_turn", content=[SimpleNamespace(type="text", text=texte, citations=[])])

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def __iter__(self):
        return iter(self.evenements)

    def get_final_message(self):
        return self.message


@pytest.fixture
def claude_principal(monkeypatch):
    """Claude en IA principale (AI_PRINCIPALE=claude), avec le vrai `claude_events` et un faux client Anthropic."""
    import services.backup_ai as backup_ai

    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("AI_PRINCIPALE", "claude")
    monkeypatch.setattr(app_module.client.responses, "create", lambda **kw: (_ for _ in ()).throw(AssertionError("OpenAI appelé")))

    def install(blocs, texte):
        monkeypatch.setattr(backup_ai, "_client", lambda: SimpleNamespace(
            beta=SimpleNamespace(messages=SimpleNamespace(stream=lambda **params: _FluxClaude(blocs, texte)))))

    return install


def test_claude_annonce_aussi_sa_recherche_web(claude_principal):
    """Choix du propriétaire (25 octobre 2026) : Claude Opus est l'IA principale ; la phrase d'attente doit rester."""
    texte = "Selon les sources consultées, le TER circule normalement cette semaine."
    recherche = SimpleNamespace(type="server_tool_use", name="web_search", id="srvtoolu_1", input={})
    resultat = SimpleNamespace(type="web_search_tool_result", tool_use_id="srvtoolu_1", content=[])
    claude_principal([recherche, resultat, recherche, resultat], texte)
    events = _events("Quelles sont les dernières nouvelles sur le BRT de Dakar ?")
    statuts = [i for i, e in enumerate(events) if "st" in e]
    assert [events[i] for i in statuts] == [{"st": "web"}]
    assert statuts[0] < next(i for i, e in enumerate(events) if "d" in e)
    assert texte in "".join(e.get("d", "") for e in events)


def test_claude_sans_recherche_n_annonce_rien(claude_principal):
    texte = "Le thiéboudienne est le plat national du Sénégal."
    claude_principal([], texte)
    events = _events("Parle-moi du thiéboudienne et de ses origines")
    assert not any("st" in e for e in events)
    assert texte in "".join(e.get("d", "") for e in events)


def test_la_page_affiche_la_phrase_d_attente_en_francais_et_en_anglais():
    assert "searching:'Je cherche des informations à jour…'" in HOME_JS
    assert "searching:'Looking for up-to-date information…'" in HOME_JS
    # L'événement n'est lu que tant que les points sont affichés, et la phrase est annoncée aux lecteurs d'écran.
    assert re.search(r"if\(ev\.st==='web'\)", HOME_JS)
    assert "role','status'" in HOME_JS or 'role="status"' in HOME_JS
