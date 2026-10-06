"""SEO interne : les nouvelles pages stratégiques restent accessibles depuis l'accueil."""


def test_home_links_to_priority_seo_pages():
    from app import app

    page = app.test_client().get("/", base_url="https://teranga-ai.fr")
    assert page.status_code == 200
    body = page.get_data(as_text=True)
    for path in (
        "/voyage-senegal",
        "/transport-senegal",
        "/vie-pratique-senegal",
        "/emploi-senegal",
        "/formation-senegal",
        "/entreprendre-senegal",
    ):
        assert f'href="{path}"' in body
