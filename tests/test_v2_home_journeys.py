from pathlib import Path


HOME = Path(__file__).resolve().parents[1] / "templates" / "home.html"


def test_home_exposes_v2_product_journeys():
    html = HOME.read_text(encoding="utf-8")
    assert 'id="journeyStrip"' in html
    assert 'data-journey="plan"' in html
    assert 'data-journey="discover"' in html
    assert 'data-journey="chat"' in html
    assert "window.location.href='/trip-planner?lang='" in html
    assert "window.location.href='/explorer'" in html


def test_home_persists_selected_journey_for_session():
    html = HOME.read_text(encoding="utf-8")
    assert "sessionStorage.setItem('teranga-journey',journey)" in html


def test_home_renders_journey_labels_after_language_change():
    html = HOME.read_text(encoding="utf-8")
    assert "function renderJourneyLabels()" in html
    assert "renderJourneyLabels();" in html


def test_home_exposes_teranga_project_builder():
    html = HOME.read_text(encoding="utf-8")
    assert 'data-journey="project"' in html
    assert 'id="projectModal"' in html
    assert 'id="projectForm"' in html
    assert "postJSON('/api/projects/plan'" in html
    assert "teranga-project-last" in html


def test_home_exposes_project_progression():
    html = HOME.read_text(encoding="utf-8")
    assert "function renderProjectProgress(container,project)" in html
    assert "localStorage.setItem('teranga-project-last'" in html
    assert "Idée" in html
    assert "Premiers clients" in html
