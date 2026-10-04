from home_source import home_source
from pathlib import Path


HOME = Path(__file__).resolve().parents[1] / "templates" / "home.html"


def test_home_exposes_v2_product_journeys():
    html = home_source()
    assert 'id="journeyStrip"' in html
    assert 'data-journey="travel"' in html
    assert 'data-journey="project"' in html
    assert 'data-journey="discover"' in html
    assert 'data-journey="chat"' in html
    assert "window.location.href='/trip-planner?lang='" in html


def test_home_reduces_landing_to_four_primary_journeys():
    html = home_source()
    assert 'data-journey="travel"' in html
    assert 'data-journey="project"' in html
    assert 'data-journey="discover"' in html
    assert 'data-journey="chat"' in html
    assert '#audienceMode{display:none!important}' in html


def test_home_persists_selected_journey_for_session():
    html = home_source()
    assert "sessionStorage.setItem('teranga-journey',journey)" in html


def test_home_renders_journey_labels_after_language_change():
    html = home_source()
    assert "function renderJourneyLabels()" in html
    assert "renderJourneyLabels();" in html


def test_home_exposes_teranga_project_builder():
    html = home_source()
    assert 'data-journey="project"' in html
    assert 'id="projectModal"' in html
    assert 'id="projectForm"' in html
    assert "postJSON('/api/projects/plan'" in html
    assert 'id="projectCategory"' in html
    assert 'Une idée suffit. Teranga construit le premier plan avec toi.' in html
    assert 'Ajouter des détails (facultatif)' in html
    assert '🚀 Générer mon projet' in html
    assert 'id="projectNew"' in html
    assert "projectForm').hidden=true" in html
    assert "teranga-project-last" in html


def test_home_exposes_project_progression():
    html = home_source()
    assert "function renderProjectProgress(container,project)" in html
    assert "localStorage.setItem('teranga-project-last'" in html
    assert "Idée" in html
    assert "Premiers clients" in html


def test_home_links_project_builder_to_partner_directory():
    html = home_source()
    assert 'href="/partners"' in html
    assert "Trouver un partenaire" in html
