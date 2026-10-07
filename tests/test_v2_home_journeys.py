from home_source import home_source
from pathlib import Path


HOME = Path(__file__).resolve().parents[1] / "templates" / "home.html"


def test_home_exposes_v2_product_journeys():
    html = home_source()
    assert 'id="journeyStrip"' in html
    assert 'data-journey="travel"' in html
    assert 'data-journey="project"' not in html  # intégré au chat
    assert 'data-journey="discover"' in html
    assert 'data-journey="chat"' in html
    assert "window.location.href='/trip-planner?lang='" in html


def test_home_reduces_landing_to_three_primary_journeys():
    html = home_source()
    assert 'data-journey="travel"' in html
    assert 'data-journey="project"' not in html
    assert 'data-journey="discover"' in html
    assert 'data-journey="chat"' in html
    # Design v2 : les profils (touriste, résident…) restent visibles sur téléphone.
    assert '#audienceMode{display:none!important}' not in html


def test_home_mobile_tabbar_links_to_places_trip_and_emergency():
    html = home_source()
    assert 'href="/lieux" data-tab="places"' in html
    assert 'href="/trip-planner" data-tab="trip"' in html
    assert 'href="/urgences" data-tab="sos"' in html
    assert "navPlaces:'Lieux'" in html and "navSos:'Emergency'" in html


def test_home_persists_selected_journey_for_session():
    html = home_source()
    assert "SS.setItem('teranga-journey',journey)" in html


def test_home_renders_journey_labels_after_language_change():
    html = home_source()
    assert "function renderJourneyLabels()" in html
    assert "renderJourneyLabels();" in html


def test_home_exposes_teranga_project_builder_inside_chat():
    html = home_source()
    # Plus de bouton d'accueil : le chat propose le plan après une réponse « projet ».
    assert "if(ux&&ux.intent==='project')addProjectOffer(wait.col,text);" in html
    assert "postJSON('/api/projects/plan',JSON.stringify({idea}))" in html
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
    assert "LS.setItem('teranga-project-last'" in html
    assert "Idée" in html
    assert "Premiers clients" in html


def test_home_links_project_builder_to_partner_directory():
    html = home_source()
    assert 'href="/partners"' in html
    assert "Trouver un partenaire" in html


def test_home_v2_hero_matches_mockup():
    html = home_source()
    assert 'id="heroAsk"' in html and 'id="heroInput"' in html and 'id="heroMic"' in html
    assert 'href="/lieux/goree"' in html and 'href="/lieux/lac-rose"' in html
    assert 'href="/trip-planner"' in html and "planTitle:'Planifier mon voyage'" in html
    # Micro : icône au trait, plus d'émoji.
    assert ">🎤<" not in html
