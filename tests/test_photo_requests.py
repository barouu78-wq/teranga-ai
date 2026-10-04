"""« Montre-moi les photos de Dakar » : texte exact, langue, wolof, échec honnête."""

import json
import os

import pytest

os.environ.setdefault("OPENAI_API_KEY", "test-key")


@pytest.fixture
def photo_client(monkeypatch):
    import app as app_module
    import services.image_topics as image_topics

    image_topics._TOPIC_IMAGE_CACHE.clear()
    state = {"photos": True, "queries": []}

    def fake_google(title, limit=4):
        state["queries"].append(title)
        if not state["photos"]:
            return []
        return [{"url": f"https://upload.wikimedia.org/{i}.jpg", "display_url": f"/og.png?{i}", "alt": title} for i in range(3)]

    monkeypatch.setattr(app_module, "GOOGLE_API_KEY", "k")
    monkeypatch.setattr(app_module, "GOOGLE_CSE_ID", "cx")
    monkeypatch.setattr(app_module, "fetch_google_images", fake_google)
    monkeypatch.setattr(app_module, "fetch_commons_images", lambda title, limit=4: [])
    monkeypatch.setattr(app_module, "fetch_city_image", lambda title: None)
    client = app_module.app.test_client()
    token = client.get("/csrf", base_url="https://teranga-ai.fr").get_json()["token"]
    client.set_cookie("teranga_csrf", token, domain="teranga-ai.fr")

    def ask(message, language="fr"):
        image_topics._TOPIC_IMAGE_CACHE.clear()
        response = client.post(
            "/chat",
            json={"message": message, "language": language},
            headers={"X-CSRF-Token": token, "Origin": "https://teranga-ai.fr"},
            base_url="https://teranga-ai.fr",
        )
        events = [json.loads(line) for line in response.get_data(as_text=True).splitlines() if line]
        text = " ".join(event["d"] for event in events if "d" in event)
        images = next((event["img"] for event in events if "img" in event), [])
        return text, images

    yield state, ask
    image_topics._TOPIC_IMAGE_CACHE.clear()


def test_dakar_photos_name_the_subject(photo_client):
    state, ask = photo_client
    text, images = ask("montre moi les photos de Dakar")
    assert text == "Voici quelques photos pour « Dakar »."
    assert len(images) == 3
    assert state["queries"] == ["Dakar"]


def test_english_request_gets_english_text(photo_client):
    _, ask = photo_client
    text, _ = ask("show me photos of Dakar", language="en")
    assert text.startswith("Here are some photos for “Dakar”")


def test_wolof_nataal_is_a_photo_request(photo_client):
    _, ask = photo_client
    text, images = ask("nataal yu Dakar", language="wo")
    assert images and "Dakar" in text


def test_no_photo_found_is_said_honestly(photo_client):
    state, ask = photo_client
    state["photos"] = False
    text, images = ask("montre moi les photos de Dakar")
    assert images == []
    assert text.startswith("Je n'ai pas trouvé de photo fiable")
    assert "Voici" not in text


def test_city_request_is_not_captured_by_a_landmark_short_name():
    from app import knowledge_image_titles

    titles = knowledge_image_titles("montre moi les photos de Dakar")
    assert titles[0] == "Dakar"
    assert not any("Corniche" in title for title in titles)
