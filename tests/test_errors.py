from services.errors import public_error


def test_public_error_redacts_api_key_and_maps_authentication():
    message = public_error(RuntimeError("401 api_key=sk-abcdefghijklmnopqrstuvwxyz"))
    assert message == "Le service IA est momentanément indisponible. Réessaie dans quelques secondes."
    assert "sk-" not in message


def test_public_error_maps_timeout():
    assert public_error(TimeoutError("request timed out")) == "La réponse a pris trop de temps. Réessaie."


def test_public_error_maps_provider_rate_limit():
    assert public_error(RuntimeError("429 quota exceeded")) == "Le service est très demandé. Réessaie dans un moment."


def test_public_error_maps_unknown_failure():
    assert public_error(RuntimeError("unexpected failure")) == "Le service IA a rencontré une erreur inattendue. Réessaie dans quelques secondes."
