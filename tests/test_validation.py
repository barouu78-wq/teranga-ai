from services.validation import normalize, sanitize_text


def test_normalize_is_case_and_accent_insensitive():
    assert normalize("  Île de Gorée  ") == "ile de goree"


def test_sanitize_text_removes_control_and_zero_width_characters():
    assert sanitize_text(" bon\u200bjour\x00  à  tous ", 100) == "bonjour à tous"


def test_sanitize_text_respects_max_length():
    assert sanitize_text("abcdef", 3) == "abc"
