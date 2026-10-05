"""Secondary pages share one stylesheet, header and footer (design v6)."""

import os

import pytest

os.environ.setdefault("OPENAI_API_KEY", "test-key")

PAGES = [
    "/explorer",
    "/lieux",
    "/lieux/goree",
    "/dakar",
    "/regions/dakar",
    "/en/senegal-travel-guide",
    "/trip-planner?lang=fr",
    "/opportunities",
    "/partners",
]


@pytest.mark.parametrize("path", PAGES)
def test_secondary_pages_use_shared_layout(path):
    from app import app

    html = app.test_client().get(path).get_data(as_text=True)
    assert '<link rel="stylesheet" href="/static/site.css?v=' in html
    assert '<script src="/static/theme.js?v=' in html
    assert 'class="site-header"' in html and 'class="site-footer"' in html
    # Plus de fond sombre codé en dur propre à chaque page.
    assert "background:#0b0907" not in html


def test_shared_assets_are_served_and_cached():
    from app import app

    client = app.test_client()
    for path, mimetype in (("/static/site.css", "text/css"), ("/static/theme.js", "text/javascript")):
        response = client.get(path)
        assert response.status_code == 200
        assert response.mimetype == mimetype
        assert response.headers["Cache-Control"] == "public, max-age=3600"


def test_public_pages_no_longer_advertise_pulaar_in_footer():
    from app import app

    html = app.test_client().get("/dakar").get_data(as_text=True)
    assert "WO · PU" not in html


def test_filter_forms_have_accessible_labels():
    from app import app

    client = app.test_client()
    partners = client.get("/partners").get_data(as_text=True)
    assert '<select name="category" aria-label="Secteur">' in partners
    assert 'aria-label="Ville"' in partners
    assert 'aria-label="Domaine"' in client.get("/opportunities").get_data(as_text=True)


@pytest.mark.parametrize("path", ["/trip-planner?lang=fr", "/opportunities", "/partners"])
def test_pages_have_meta_description(path):
    from app import app

    assert '<meta name="description" content="' in app.test_client().get(path).get_data(as_text=True)


def test_regional_ambiance_on_place_and_region_pages():
    from app import app
    from services.site_layout import region_ambiance

    assert region_ambiance("Saint-Louis") == "saint-louis"
    assert region_ambiance("Sédhiou") == "casamance" and region_ambiance("Ziguinchor") == "casamance"
    assert region_ambiance("Dakar") == ""
    client = app.test_client()
    assert '<body data-ambiance="saint-louis">' in client.get("/lieux/saint-louis").get_data(as_text=True)
    assert '<body data-ambiance="casamance">' in client.get("/regions/kolda").get_data(as_text=True)
    assert "data-ambiance" not in client.get("/lieux/goree").get_data(as_text=True)
