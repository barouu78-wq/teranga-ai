import os

os.environ.setdefault("OPENAI_API_KEY", "test-key")


def test_download_page_offers_the_apk_and_announces_google_play(monkeypatch):
    from app import app
    from routes.android import APK_URL, PLAY_URL

    monkeypatch.delenv("ANDROID_PLAY_PUBLIC", raising=False)
    response = app.test_client().get("/telecharger")
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert f'href="{APK_URL}"' in html and "Télécharger l&#x27;APK" in html
    assert "Bientôt sur Google Play" in html and PLAY_URL not in html


def test_google_play_button_appears_once_the_app_is_public(monkeypatch):
    from app import app
    from routes.android import PLAY_URL

    monkeypatch.setenv("ANDROID_PLAY_PUBLIC", "1")
    html = app.test_client().get("/telecharger").get_data(as_text=True)
    assert f'href="{PLAY_URL}"' in html and "Bientôt" not in html


def test_download_page_is_in_the_sitemap():
    from app import app

    assert "/telecharger</loc>" in app.test_client().get("/sitemap.xml").get_data(as_text=True)


def test_testers_section_links_the_group_and_the_play_opt_in(monkeypatch):
    from app import app
    from routes.android import TESTERS_GROUP_URL, TESTING_OPT_IN_URL

    monkeypatch.delenv("ANDROID_PLAY_PUBLIC", raising=False)
    html = app.test_client().get("/telecharger").get_data(as_text=True)
    assert "Deviens testeur" in html
    assert html.index(TESTERS_GROUP_URL) < html.index(TESTING_OPT_IN_URL)
    monkeypatch.setenv("ANDROID_PLAY_PUBLIC", "1")
    assert "Deviens testeur" not in app.test_client().get("/telecharger").get_data(as_text=True)


def test_home_page_links_to_the_android_download_page():
    from app import app

    html = app.test_client().get("/").get_data(as_text=True)
    assert 'id="planCta" href="/telecharger"' in html


def test_home_links_to_the_cv_builder():
    from app import app

    html = app.test_client().get("/").get_data(as_text=True)
    assert 'id="cvCta" href="/cv"' in html and "Faire mon CV gratuit" in html


def test_job_guide_button_leads_to_the_cv_builder():
    from app import app

    client = app.test_client()
    emploi = client.get("/emploi-senegal").get_data(as_text=True)
    assert '<a class="cta primary" href="/cv">Faire mon CV gratuit</a>' in emploi
    # Les autres pages guides gardent leur bouton vers l'assistant.
    assert 'href="/cv">Faire mon CV gratuit' not in client.get("/formation-senegal").get_data(as_text=True)
