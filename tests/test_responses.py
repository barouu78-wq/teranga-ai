from services.responses import event_delta, extract_sources


def test_event_delta_supports_response_text_events():
    class Event:
        type = "response.output_text.delta"
        delta = "Bonjour"

    assert event_delta(Event()) == "Bonjour"


def test_extract_sources_deduplicates_and_filters_provider_hosts():
    source = {
        "type": "url_citation",
        "url": "https://example.com/page#section",
        "title": "Example",
    }
    result = extract_sources(
        {"citations": [source, source]},
        {"url": "https://openai.com/internal", "title": "Provider"},
    )
    assert result == [{"title": "Example", "url": "https://example.com/page#section"}]
