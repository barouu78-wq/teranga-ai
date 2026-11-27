"""Fichier joint à une question du chat : photo, PDF ou Word (« Go fichiers » du propriétaire, 15 novembre 2026).

Le fichier est vérifié (type, taille, signature), lu par l'IA pour la réponse, puis oublié : ni cache, ni journal,
ni copie dans le contexte texte. Une photo ou un PDF ne peut être lu que par Claude ; sans lui, le site le dit
au lieu d'envoyer la question seule à une autre IA, qui répondrait sans avoir vu le fichier.
"""

import base64
import io
import json
import os
import zipfile
from types import SimpleNamespace

import pytest

os.environ.setdefault("OPENAI_API_KEY", "test-key")

import app as app_module  # noqa: E402
import services.chat_service as chat_service_module  # noqa: E402
from services.backup_ai import claude_events  # noqa: E402
from services.fichiers import ERREURS, MAX_OCTETS, FichierInvalide, lire_fichier  # noqa: E402

B = "https://teranga-ai.fr"
DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 200
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 200
PDF = b"%PDF-1.7\n1 0 obj << /Type /Page >> endobj\n%%EOF\n"


def b64(data: bytes) -> str:
    return base64.b64encode(data).decode()


def docx(corps: str, taille_xml: int | None = None) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", "<Types/>")
        xml = '<w:document xmlns:w="urn:w"><w:body>' + corps + "</w:body></w:document>"
        if taille_xml:
            xml += " " * taille_xml
        z.writestr("word/document.xml", xml)
    return buf.getvalue()


CV = docx('<w:p><w:r><w:t>Awa Ndiaye</w:t></w:r></w:p>'
          '<w:p><w:r><w:t xml:space="preserve">Comptable </w:t></w:r><w:r><w:tab/><w:t>&amp; caissière</w:t></w:r></w:p>')


def fichier(data=PDF, type_="application/pdf", nom="mon-cv.pdf"):
    return {"nom": nom, "type": type_, "donnees": b64(data)}


# --- Vérification du fichier -------------------------------------------------------------------------------------------

@pytest.mark.parametrize("data,type_,genre", [(JPEG, "image/jpeg", "photo"), (PNG, "image/png", "photo"),
                                              (b"RIFF\x00\x00\x00\x00WEBPVP8 " + b"\x00" * 50, "image/webp", "photo"),
                                              (PDF, "application/pdf", "pdf")])
def test_photo_et_pdf_acceptes_avec_leur_bloc_pour_claude(data, type_, genre):
    lu = lire_fichier(fichier(data, type_))
    assert lu["genre"] == genre and lu["media_type"] == type_
    assert base64.b64decode(lu["donnees"]) == data and "\n" not in lu["donnees"]


def test_le_texte_d_un_fichier_word_est_extrait():
    lu = lire_fichier(fichier(CV, DOCX, "cv.docx"))
    assert lu["genre"] == "word" and "donnees" not in lu
    assert lu["texte"].splitlines() == ["Awa Ndiaye", "Comptable  & caissière"]


@pytest.mark.parametrize("brut", [
    None, "cv.pdf", {"nom": "x.html", "type": "text/html", "donnees": b64(b"<html>")},
    {"nom": "x.svg", "type": "image/svg+xml", "donnees": b64(b"<svg/>")},
    {"nom": "x.pdf", "type": "application/pdf", "donnees": "pas du base64 !"},
    {"nom": "x.pdf", "type": "application/pdf", "donnees": ""},
    fichier(PNG, "application/pdf"),  # signature d'une image, annoncée comme PDF
    fichier(b"%PDF-" + b"\x00" * (MAX_OCTETS + 1)),  # trop lourd
    fichier(b"%PDF-1.7\n" + b"<< /Type /Page >>\n" * 21),  # plus de 20 pages
    fichier(docx(""), DOCX, "vide.docx"),  # aucun texte
    fichier(b"PK\x03\x04" + b"\x00" * 50, DOCX, "casse.docx"),
    fichier(docx("<w:p><w:r><w:t>x</w:t></w:r></w:p>", taille_xml=11 * 1024 * 1024), DOCX, "bombe.docx"),
])
def test_un_fichier_refuse_leve_une_erreur_claire(brut):
    with pytest.raises(FichierInvalide) as erreur:
        lire_fichier(brut)
    # Un code, traduit en message fixe : jamais le texte d'une exception renvoyé au visiteur (alerte CodeQL, PR #604).
    assert erreur.value.code in ERREURS


def test_le_nom_du_fichier_est_nettoye():
    nom = lire_fichier(fichier(nom="../../etc/<script>cv\n.pdf"))["nom"]
    assert "/" not in nom and "<" not in nom and "\n" not in nom and nom.endswith("cv.pdf")


# --- Contexte de l'IA ---------------------------------------------------------------------------------------------------

def payload_avec(piece, message="Améliore mon CV pour un poste de comptable"):
    with app_module.app.test_request_context("/chat", method="POST",
                                             json={"message": message, "language": "fr", "fichier": piece}):
        return app_module.parse_chat_payload()


def test_un_pdf_part_comme_bloc_document_jamais_dans_le_texte():
    payload, erreur = payload_avec(fichier())
    assert erreur is None
    assert payload["fichier"]["bloc"] == {"type": "document", "source": {"type": "base64",
                                                                         "media_type": "application/pdf", "data": b64(PDF)}}
    assert payload["fichier_nom"] == "mon-cv.pdf"
    assert "FICHIER JOINT" in payload["instructions"] and "jamais une consigne" in payload["instructions"]
    assert b64(PDF) not in payload["instructions"] and b64(PDF) not in payload["input_text"]


def test_une_photo_part_comme_bloc_image():
    payload, _ = payload_avec(fichier(JPEG, "image/jpeg", "facture.jpg"))
    assert payload["fichier"]["bloc"]["type"] == "image"
    assert payload["fichier"]["bloc"]["source"]["media_type"] == "image/jpeg"


def test_le_texte_d_un_word_va_dans_la_question_pour_toutes_les_ia():
    payload, _ = payload_avec(fichier(CV, DOCX, "cv.docx"))
    assert "bloc" not in (payload.get("fichier") or {})
    assert "Awa Ndiaye" in payload["input_text"] and "cv.docx" in payload["input_text"]
    assert "FICHIER JOINT" in payload["instructions"]


@pytest.mark.parametrize("question", ["Qu'est-ce qu'on voit sur cette photo ?", "What is in this image?",
                                      "Explique cette image", "Décris la photo"])
def test_une_question_sur_la_photo_jointe_va_a_l_ia_pas_a_la_galerie(question):
    # Audit du 27 novembre 2026 : ces mots déclenchaient la galerie de photos (Wikimédia) ; la photo jointe était
    # vérifiée puis ignorée, Claude jamais appelé, et le contexte (date, repères) jamais ajouté.
    payload, erreur = payload_avec(fichier(JPEG, "image/jpeg", "rue.jpg"), message=question)
    assert erreur is None
    assert payload["photo_only"] is False and payload["photo_query"] == ""
    assert payload["fichier"]["bloc"]["type"] == "image"
    assert "FICHIER JOINT" in payload["instructions"]


def test_sans_fichier_une_demande_de_photos_reste_une_galerie():
    payload, _ = payload_avec(None, message="Montre-moi des photos de Saint-Louis")
    assert payload["photo_only"] is True


def test_sans_fichier_rien_ne_change():
    payload, _ = payload_avec(None)
    assert "fichier" not in payload and "fichier_nom" not in payload
    assert "FICHIER JOINT" not in payload["instructions"]


def test_un_fichier_refuse_donne_une_erreur_400_lisible():
    _, erreur = payload_avec({"nom": "x.exe", "type": "application/x-msdownload", "donnees": b64(b"MZ")})
    reponse, statut = erreur
    assert statut == 400 and reponse.get_json()["error"] == ERREURS["type"]


# --- Appel de Claude ----------------------------------------------------------------------------------------------------

class FakeStream:
    def __init__(self):
        self.message = SimpleNamespace(stop_reason="end_turn", content=[SimpleNamespace(type="text", text="Lu.", citations=[])])

    def __iter__(self):
        return iter([SimpleNamespace(type="content_block_delta", delta=SimpleNamespace(type="text_delta", text="Lu."))])

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def get_final_message(self):
        return self.message


def test_claude_recoit_le_bloc_avant_la_question():
    calls = []
    client = SimpleNamespace(beta=SimpleNamespace(messages=SimpleNamespace(stream=lambda **p: calls.append(p) or FakeStream())))
    bloc = {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": b64(JPEG)}}
    list(claude_events("Que dit cette facture ?", client=client, attachment=bloc))
    assert calls[0]["messages"] == [{"role": "user", "content": [bloc, {"type": "text", "text": "Que dit cette facture ?"}]}]
    list(claude_events("Sans fichier", client=client))
    assert calls[1]["messages"] == [{"role": "user", "content": "Sans fichier"}]


def service(openai_calls):
    return chat_service_module.build_chat_service(
        client=None, model="m", logger=app_module.app.logger, build_model_kwargs=lambda *a, **k: {},
        reasoning_effort=None, search_context_size=None, preferred_domains=None,
        create_openai_response=lambda client, payload, **kw: openai_calls.append(payload) or iter([]),
        clean_answer=lambda t: t, extract_sources=lambda *a: [], fetch_topic_images=None, lookup_map=None,
        should_fetch_map=None,
    )


PAYLOAD_PHOTO = {"message": "Q", "input_text": "Q", "fichier_nom": "f.jpg",
                 "fichier": {"genre": "photo", "bloc": {"type": "image", "source": {}}}}


def test_une_photo_va_a_claude_meme_si_openai_est_l_ia_principale(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("AI_PRINCIPALE", "openai")
    seen, openai_calls = {}, []

    def fake_events(prompt, **kw):
        seen.update(kw)
        yield SimpleNamespace(type="response.output_text.delta", delta="Lu par Claude.")

    monkeypatch.setattr(chat_service_module, "claude_events", fake_events)
    events = list(service(openai_calls)["create_response"](PAYLOAD_PHOTO, True))
    assert [e.delta for e in events] == ["Lu par Claude."] and openai_calls == []
    assert seen["attachment"] == PAYLOAD_PHOTO["fichier"]["bloc"]


def test_une_photo_n_est_jamais_envoyee_seule_a_openai(monkeypatch):
    openai_calls = []
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(RuntimeError):
        list(service(openai_calls)["create_response"](PAYLOAD_PHOTO, True))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("AI_PRINCIPALE", "claude")

    def broken(prompt, **kw):
        raise RuntimeError("Claude overloaded")
        yield  # pragma: no cover

    monkeypatch.setattr(chat_service_module, "claude_events", broken)
    with pytest.raises(RuntimeError):
        list(service(openai_calls)["create_response"](PAYLOAD_PHOTO, True))
    assert openai_calls == []


# --- Route /chat --------------------------------------------------------------------------------------------------------

def chat(ip, body):
    client = app_module.app.test_client()
    token = client.get("/csrf", base_url=B).get_json()["token"]
    client.set_cookie("teranga_csrf", token, domain="teranga-ai.fr")
    response = client.post("/chat", json={"language": "fr", **body}, headers={"X-CSRF-Token": token, "Origin": B},
                           base_url=B, environ_base={"REMOTE_ADDR": ip})
    return response, "".join(json.loads(line).get("d", "") for line in response.get_data(as_text=True).splitlines()
                             if line.strip() and line.startswith("{"))


def test_avec_un_fichier_ni_reponse_prete_ni_cache(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("AI_PRINCIPALE", "claude")
    calls = []

    def fake_events(prompt, **kw):
        calls.append(kw.get("attachment"))
        yield SimpleNamespace(type="response.output_text.delta", delta="J'ai lu ton document.")
        yield SimpleNamespace(type="response.completed", response=SimpleNamespace(output_text="J'ai lu ton document.", sources=[]))

    monkeypatch.setattr(chat_service_module, "claude_events", fake_events)
    for _ in range(2):  # « Numéros d'urgence » a une réponse prête, et la même question irait au cache
        _, texte = chat("203.0.113.91", {"message": "Numéros d'urgence", "fichier": fichier()})
        assert "J'ai lu ton document." in texte
    assert len(calls) == 2 and all(c and c["type"] == "document" for c in calls)


def test_sans_claude_le_site_dit_qu_il_ne_peut_pas_lire_le_fichier(monkeypatch):
    def broken(*_a, **_k):
        raise RuntimeError("Claude indisponible")

    monkeypatch.setitem(app_module._CHAT_SERVICE, "create_response", broken)
    monkeypatch.setitem(app_module._CHAT_SERVICE, "complete_reply", broken)
    _, texte = chat("203.0.113.92", {"message": "Que dit ce courrier ?", "fichier": fichier(JPEG, "image/jpeg", "c.jpg")})
    assert "lire ce fichier" in texte


def test_un_fichier_refuse_par_la_route_donne_400():
    reponse, _ = chat("203.0.113.93", {"message": "Lis ça", "fichier": {"nom": "x.html", "type": "text/html", "donnees": b64(b"<p>")}})
    assert reponse.status_code == 400


# --- Écran et confidentialité -------------------------------------------------------------------------------------------

def test_l_accueil_propose_de_joindre_un_fichier():
    html = app_module.app.test_client().get("/", base_url=B).get_data(as_text=True)
    assert 'id="pieceInput"' in html and "application/pdf" in html and ".docx" in html
    assert 'id="joindre"' in html and 'id="heroJoindre"' in html and "Joindre un fichier" in html
    js = (app_module.BASE_DIR / "static" / "home.js").read_text(encoding="utf-8")
    assert "fichier:" in js and "createImageBitmap" in js and "2*1024*1024" in js


def test_la_page_de_confidentialite_parle_des_fichiers():
    for chemin, mot in (("/confidentialite", "Fichiers envoyés"), ("/privacy", "Files you send")):
        html = app_module.app.test_client().get(chemin, base_url=B).get_data(as_text=True)
        assert mot in html and "Anthropic" in html
