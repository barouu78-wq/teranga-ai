"""« Plus de photos » : la suite de la galerie, sur le même sujet, sans répéter les photos déjà montrées.

Signalé par le propriétaire le 24 octobre 2026 : « Quand je lui demande plus de photos, il me renvoie la même chose ».
Deux causes : le bouton « Plus de photos » (et « D'autres photos ») envoyait une demande sans sujet, cherchée telle
quelle (« Voici quelques photos pour « Plus de photos » ») ; et « Encore des photos de Gorée » refaisait la même
recherche, donc la même galerie. Comme en production (Google refusé, photos des articles Wikipédia), les faux
fournisseurs ci-dessous n'ont qu'un nombre fini de photos.
"""

import json
import os

import pytest

os.environ.setdefault("OPENAI_API_KEY", "test-key")

from services.chat_payload_service import photo_page, photo_request  # noqa: E402

GOREE = [
    {"role": "user", "content": "Montre-moi des photos de Gorée"},
    {"role": "assistant", "content": "Voici quelques photos pour « Île de Gorée »."},
]


@pytest.mark.parametrize("suite", ["Plus de photos", "D'autres photos", "d’autres photos stp", "Encore des photos",
                                   "Montre-moi plus de photos", "More photos", "Une autre photo"])
def test_une_suite_sans_sujet_garde_le_sujet_de_la_galerie(suite):
    assert photo_request(suite, GOREE + [{"role": "user", "content": suite}]) == (True, "Montre-moi des photos de Gorée")
    assert photo_page(suite, GOREE) == 1


def test_chaque_nouvelle_suite_passe_a_la_page_suivante():
    deux = GOREE + [{"role": "user", "content": "Plus de photos"}, {"role": "assistant", "content": "Voici d'autres photos."}]
    assert photo_request("Plus de photos", deux) == (True, "Montre-moi des photos de Gorée")
    assert photo_page("Plus de photos", deux) == 2


def test_encore_des_photos_du_meme_lieu_est_une_suite():
    assert photo_request("Encore des photos de Gorée", GOREE) == (True, "Montre-moi des photos de Gorée")
    assert photo_page("Encore des photos de Gorée", GOREE) == 1


@pytest.mark.parametrize("demande", ["Plus de photos de Dakar", "Montre-moi des photos de Dakar",
                                     "Montre-moi des photos d'autres plages"])
def test_un_autre_sujet_repart_de_la_premiere_page(demande):
    assert photo_request(demande, GOREE) == (True, demande)
    assert photo_page(demande, GOREE) == 0


def test_une_premiere_demande_est_la_premiere_page():
    assert photo_page("Montre-moi des photos de Gorée", []) == 0
    assert photo_page("Parle-moi de Gorée", GOREE) == 0


def test_plus_de_photos_apres_une_reponse_illustree_suit_la_question():
    """Le bouton « Plus de photos » suit aussi une réponse du modèle illustrée (« … et montre la ville »)."""
    question = "Raconte brièvement l'histoire de Dakar et montre la ville."
    historique = [{"role": "user", "content": question}, {"role": "assistant", "content": "Dakar est la capitale…"}]
    assert photo_request("Plus de photos", historique) == (True, f"photos : {question}")
    assert photo_page("Plus de photos", historique) == 1
    # Sans galerie dans la réponse (rien à « voir »), la première page n'a pas encore été montrée.
    sans_photo = [{"role": "user", "content": "Parle-moi de Saly"}, {"role": "assistant", "content": "Saly est…"}]
    assert photo_request("Plus de photos", sans_photo) == (True, "photos : Parle-moi de Saly")
    assert photo_page("Plus de photos", sans_photo) == 0


# --- Parcours complet par /chat -------------------------------------------------------------------------------------

@pytest.fixture
def galerie(monkeypatch):
    import app as app_module
    import services.image_topics as image_topics

    image_topics._TOPIC_IMAGE_CACHE.clear()
    state = {"articles": 12, "commons": 0}

    def fake_article(title, limit=6):
        slug = title.replace(" ", "_")
        return [{"url": f"https://upload.wikimedia.org/{slug}/{i}.jpg", "alt": title}
                for i in range(min(limit, state["articles"]))]

    def fake_commons(title, limit=4):
        slug = title.replace(" ", "_")
        return [{"url": f"https://upload.wikimedia.org/commons/{slug}/{i}.jpg", "alt": title}
                for i in range(min(limit, state["commons"]))]

    monkeypatch.setattr(app_module, "fetch_google_images", lambda title, limit=4: [])
    monkeypatch.setattr(app_module, "fetch_article_images", fake_article)
    monkeypatch.setattr(app_module, "fetch_commons_images", fake_commons)
    monkeypatch.setattr(app_module, "fetch_city_image", lambda title: None)
    client = app_module.app.test_client()
    token = client.get("/csrf", base_url="https://teranga-ai.fr").get_json()["token"]
    client.set_cookie("teranga_csrf", token, domain="teranga-ai.fr")
    history = []

    def ask(message):
        history.append({"role": "user", "content": message})
        response = client.post(
            "/chat",
            json={"message": message, "language": "fr", "history": history},
            headers={"X-CSRF-Token": token, "Origin": "https://teranga-ai.fr"},
            base_url="https://teranga-ai.fr",
            environ_base={"REMOTE_ADDR": "203.0.113.47"},
        )
        events = [json.loads(line) for line in response.get_data(as_text=True).splitlines() if line]
        text = " ".join(event["d"] for event in events if "d" in event)
        history.append({"role": "assistant", "content": text})
        images = next((event["img"] for event in events if "img" in event), [])
        return text, [photo["url"] for photo in images]

    yield state, ask
    image_topics._TOPIC_IMAGE_CACHE.clear()


def test_plus_de_photos_montre_de_nouvelles_photos_du_meme_lieu(galerie):
    _, ask = galerie
    texte, premieres = ask("Montre-moi des photos de Gorée")
    assert len(premieres) == 8 and "Gorée" in texte

    texte, suivantes = ask("Plus de photos")
    assert suivantes, texte
    assert not set(suivantes) & set(premieres)
    assert all("Gor" in url for url in suivantes)
    assert texte.startswith("Voici d'autres photos pour « ") and "Gorée" in texte
    assert "Plus de photos" not in texte


def test_quand_il_n_y_a_plus_de_nouvelles_photos_teranga_le_dit(galerie):
    """Deux articles (Île de Gorée, Maison des Esclaves) de 12 photos chacun : 24 photos, puis plus rien."""
    _, ask = galerie
    _, vues = ask("Montre-moi des photos de Gorée")
    for _ in range(5):
        texte, nouvelles = ask("Plus de photos")
        if not nouvelles:
            break
        assert not set(nouvelles) & set(vues), "une photo déjà montrée revient"
        vues += nouvelles
    assert nouvelles == []
    assert texte.startswith("Je n'ai pas trouvé d'autres photos fiables")
    assert len(vues) == len(set(vues)) == 24


def test_les_photos_de_commons_completent_la_suite(galerie):
    state, ask = galerie
    state["commons"] = 30
    _, premieres = ask("Montre-moi des photos de Gorée")
    _, suivantes = ask("Plus de photos")
    _, troisiemes = ask("D'autres photos")
    assert troisiemes and all("Gor" in url for url in troisiemes)
    assert not set(troisiemes) & (set(premieres) | set(suivantes))
