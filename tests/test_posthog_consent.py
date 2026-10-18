from types import SimpleNamespace

from services.posthog_consent import inject_posthog, posthog_config, posthog_tag


def test_config_requires_valid_project_key_and_https_origins():
    assert posthog_config("", "https://us.i.posthog.com", "https://us-assets.i.posthog.com") is None
    assert posthog_config("phc_test", "http://us.i.posthog.com", "https://us-assets.i.posthog.com") is None
    assert posthog_config("phc_test", "https://us.i.posthog.com", "https://us-assets.i.posthog.com") == {
        "project_key": "phc_test",
        "api_host": "https://us.i.posthog.com",
        "asset_host": "https://us-assets.i.posthog.com",
        "api_origin": "https://us.i.posthog.com",
        "asset_origin": "https://us-assets.i.posthog.com",
    }


def test_tag_escapes_values_and_is_local():
    config = posthog_config('phc_" onclick="x', "https://api.example", "https://assets.example")
    assert config is None
    tag = posthog_tag(posthog_config("phc_test", "https://api.example", "https://assets.example"))
    assert 'src="/static/posthog-consent.js"' in tag
    assert 'data-project-key="phc_test"' in tag


def test_inject_only_buffered_success_html():
    config = posthog_config("phc_test", "https://api.example", "https://assets.example")
    response = SimpleNamespace(
        direct_passthrough=False,
        is_streamed=False,
        status_code=200,
        mimetype="text/html",
        body="<html><head></head><body>ok</body></html>",
        get_data=lambda as_text=False: "<html><head></head><body>ok</body></html>",
    )
    response.set_data = lambda body: setattr(response, "body", body)
    inject_posthog(response, config)
    assert "/static/posthog-consent.js" in response.body


def test_inject_is_noop_without_config():
    response = SimpleNamespace(direct_passthrough=False, is_streamed=False, status_code=200, mimetype="text/html")
    assert inject_posthog(response, None) is response
