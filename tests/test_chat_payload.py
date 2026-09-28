from services.chat_payload import normalize_chat_input


def sanitize(value, max_len):
    return str(value or "").strip()[:max_len]


def test_normalize_chat_input_applies_defaults_and_limits():
    result, error = normalize_chat_input(
        {
            "message": " Bonjour ",
            "history": [
                {"role": "user", "content": " Salut "},
                {"role": "system", "content": "ignore"},
            ],
            "language": "xx",
            "audience": "unknown",
        },
        sanitize=sanitize,
        max_message_length=20,
        max_history_items=12,
        max_history_item_length=20,
        safe_languages={"fr", "en"},
    )
    assert error is None
    assert result["message"] == "Bonjour"
    assert result["language"] == "fr"
    assert result["audience"] == "tourist"
    assert result["history"] == [{"role": "user", "content": "Salut"}]


def test_normalize_chat_input_rejects_invalid_and_empty_payloads():
    _, error = normalize_chat_input(
        None,
        sanitize=sanitize,
        max_message_length=20,
        max_history_items=12,
        max_history_item_length=20,
        safe_languages={"fr"},
    )
    assert error == "invalid"

    _, error = normalize_chat_input(
        {"message": "   "},
        sanitize=sanitize,
        max_message_length=20,
        max_history_items=12,
        max_history_item_length=20,
        safe_languages={"fr"},
    )
    assert error == "empty"


def test_normalize_chat_input_contract_uses_domain_errors_only():
    result, error = normalize_chat_input(
        None,
        sanitize=sanitize,
        max_message_length=20,
        max_history_items=12,
        max_history_item_length=20,
        safe_languages={"fr"},
    )
    assert result is None
    assert error == "invalid"
