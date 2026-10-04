from flask import Flask

from services.analytics import analytics_config, analytics_tag, inject_analytics
from services.http_headers import add_security_headers


def test_analytics_disabled_without_valid_https_url():
    assert analytics_config("") is None
    assert analytics_config("http://plausible.io/js/script.js") is None
    assert analytics_config("javascript:alert(1)") is None
    assert analytics_config("https://user:pw@plausible.io/js/script.js") is None


def test_analytics_tag_escapes_attributes():
    config = analytics_config("https://plausible.io/js/script.js", 'teranga-ai.fr" onload="x')
    tag = analytics_tag(config)
    assert tag.startswith('<script src="https://plausible.io/js/script.js" defer')
    assert '" onload="' not in tag


def test_inject_analytics_only_into_html_pages():
    app = Flask(__name__)
    config = analytics_config("https://plausible.io/js/script.js", "teranga-ai.fr")
    with app.test_request_context("/"):
        html = app.response_class("<html><head><title>x</title></head><body></body></html>", mimetype="text/html")
        assert "plausible.io" in inject_analytics(html, config).get_data(as_text=True)
        json_resp = app.response_class('{"a":1}', mimetype="application/json")
        assert "plausible.io" not in inject_analytics(json_resp, config).get_data(as_text=True)
        untouched = app.response_class("<html><head></head></html>", mimetype="text/html")
        assert "plausible" not in inject_analytics(untouched, None).get_data(as_text=True)


def test_csp_allows_only_configured_analytics_origin():
    app = Flask(__name__)
    with app.test_request_context("/"):
        response = add_security_headers(
            app.response_class("x"), path="/", extra_script_origins=("https://plausible.io",)
        )
        csp = response.headers["Content-Security-Policy"]
        script_src = next(part for part in csp.split(";") if part.strip().startswith("script-src"))
        connect_src = next(part for part in csp.split(";") if part.strip().startswith("connect-src"))
        assert "https://plausible.io" in script_src and "https://plausible.io" in connect_src
        default = add_security_headers(app.response_class("x"), path="/")
        assert "plausible" not in default.headers["Content-Security-Policy"]
