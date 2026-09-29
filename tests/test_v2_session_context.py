from services.explorer import render_explorer_page
from services.trip_planner import _prompt


def test_explorer_place_links_persist_context_and_offer_planner():
    html = render_explorer_page(
        [{"name": "Gorée", "type": "île", "region": "Dakar", "summary": "Patrimoine", "latitude": 14.67, "longitude": -17.40}],
        [{"id": "dakar", "name": "Dakar"}],
    )
    assert 'data-place="Gorée"' in html
    assert 'data-place-action="chat"' in html
    assert 'data-place-action="plan"' in html
    assert "teranga-place-context" in html
    assert "sessionStorage.setItem('teranga-journey',journey)" in html


def test_trip_prompt_receives_selected_place_context():
    prompt = _prompt({
        "lang": "fr",
        "arrival": "2026-10-01",
        "departure": "2026-10-03",
        "adults": 2,
        "children": 0,
        "interests": [],
        "budget": "Confort",
        "pace": "Équilibré",
        "regions": ["Dakar"],
        "context_place": "Gorée",
        "surprise": False,
    })
    assert "Selected place context: Gorée" in prompt
