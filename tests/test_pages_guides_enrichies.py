"""Pages guides proches de la page 1 de Google (Search Console, novembre 2026) : /specialites-senegal et
/entreprendre-senegal donnent des repères concrets, sans texte qui parle de l'outil au lieu du sujet. Aucun accès réseau."""

import os

os.environ.setdefault("OPENAI_API_KEY", "test-key")

import pytest  # noqa: E402

from app import app  # noqa: E402

B = "https://teranga-ai.fr"


@pytest.fixture(scope="module")
def client():
    return app.test_client()


def _page(client, path):
    response = client.get(path, base_url=B, environ_base={"REMOTE_ADDR": "203.0.113.63"})
    assert response.status_code == 200
    return response.get_data(as_text=True)


def test_cuisine_page_names_the_national_dish_and_regional_dishes(client):
    page = _page(client, "/specialites-senegal")
    for expected in ("Quel est le plat national du Sénégal ?", "UNESCO", "mbaxal", "caldou", "attaya"):
        assert expected in page
    assert "Y a-t-il des photos" not in page
    assert "pas une liste infinie" not in page


def test_business_page_points_to_the_official_procedures(client):
    page = _page(client, "/entreprendre-senegal")
    for expected in ("Où créer son entreprise au Sénégal ?", "APIX", "NINEA", "senegal.eregulations.org", "à vérifier"):
        assert expected in page
