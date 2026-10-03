            "language": "fr",
            "audience": "tourist",
        },
    ):
        payload, error = parse_chat_payload()

    assert error is None
    assert payload["use_web"] is True
    assert payload["intent_context"]["domain"] == "weather"
    assert payload["intent_context"]["preferred_sources"][:2] == ("anacim.sn", "ansd.sn")