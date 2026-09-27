from services.identity_cookie import should_set_identity_cookie


def test_identity_cookie_is_set_only_for_protected_paths_without_cookie():
    assert should_set_identity_cookie("/chat", "")
    assert should_set_identity_cookie("/tts", None)
    assert not should_set_identity_cookie("/chat", "existing")
    assert not should_set_identity_cookie("/health", "")


def test_identity_cookie_policy_normalizes_path_values_to_strings():
    assert should_set_identity_cookie("/stt", 0)
    assert not should_set_identity_cookie(None, "")
