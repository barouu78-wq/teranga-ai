"""Contrats de découverte des pages régionales pour les moteurs et assistants."""

import os

os.environ.setdefault("OPENAI_API_KEY", "test-key")


def test_llms_txt_lists_all_fourteen_regions():
    from app import app
    from services.seo import REGION_SEO_NAMES, region_slug

    page = app.test_client().get("/llms.txt", base_url="https://teranga-ai.fr")
    assert page.status_code == 200
    body = page.get_data(as_text=True)
    for region in REGION_SEO_NAMES:
        assert f"https://teranga-ai.fr/regions/{region_slug(region)}" in body


def test_sitemap_lists_all_fourteen_region_pages():
    from app import app
    from services.seo import REGION_SEO_NAMES, region_slug

    page = app.test_client().get("/sitemap.xml", base_url="https://teranga-ai.fr")
    body = page.get_data(as_text=True)
    for region in REGION_SEO_NAMES:
        assert f"https://teranga-ai.fr/regions/{region_slug(region)}" in body
