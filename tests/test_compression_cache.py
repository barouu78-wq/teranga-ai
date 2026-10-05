import gzip
import os

os.environ.setdefault("OPENAI_API_KEY", "test-key")

from flask import Flask, Response, stream_with_context

from services.compression import gzip_response


def test_home_is_gzipped_when_accepted():
    from app import app

    client = app.test_client()
    plain = client.get("/")
    compressed = client.get("/", headers={"Accept-Encoding": "gzip, deflate, br"})
    assert "Content-Encoding" not in plain.headers
    assert compressed.headers["Content-Encoding"] == "gzip"
    assert "Accept-Encoding" in compressed.headers["Vary"]
    html = gzip.decompress(compressed.data).decode("utf-8")
    assert 'id="journeyStrip"' in html
    assert len(compressed.data) < len(plain.data) / 2


def test_streamed_responses_are_never_buffered_or_compressed():
    app = Flask(__name__)

    @app.get("/stream")
    def stream():
        def generate():
            yield "a" * 2000 + "\n"
            yield "b" * 2000 + "\n"
        return Response(stream_with_context(generate()), mimetype="application/x-ndjson")

    with app.test_request_context("/stream"):
        response = app.view_functions["stream"]()
        assert gzip_response(response, "gzip") is response
        assert "Content-Encoding" not in response.headers
        assert response.is_streamed


def test_small_or_binary_responses_are_left_alone():
    app = Flask(__name__)
    with app.test_request_context("/"):
        small = gzip_response(app.response_class("x" * 100, mimetype="text/html"), "gzip")
        assert "Content-Encoding" not in small.headers
        png = gzip_response(app.response_class(b"\x89PNG" * 1000, mimetype="image/png"), "gzip")
        assert "Content-Encoding" not in png.headers


def test_public_pages_keep_their_cache_policy_and_private_ones_do_not():
    from app import app

    client = app.test_client()
    assert client.get("/dakar").headers["Cache-Control"] == "public, max-age=3600"
    assert client.get("/regions/dakar").headers["Cache-Control"] == "public, max-age=3600"
    # Accueil et fiche lieu : nonce CSP par requête → jamais en cache partagé,
    # revalidés à chaque visite mais compatibles avec le retour arrière instantané.
    assert client.get("/").headers["Cache-Control"] == "private, no-cache"
    assert client.get("/lieux/goree").headers["Cache-Control"] == "private, no-cache"
    # Données : jamais stockées.
    assert client.get("/csrf").headers["Cache-Control"] == "no-store"


def test_static_files_are_gzipped_and_versioned_ones_cached_for_a_year():
    import gzip
    import os

    os.environ.setdefault("OPENAI_API_KEY", "test-key")
    from app import app
    from services.site_layout import asset_url

    client = app.test_client()
    url = asset_url("home.js")
    response = client.get(url, headers={"Accept-Encoding": "gzip"})
    assert response.headers["Content-Encoding"] == "gzip"
    assert gzip.decompress(response.data) == open("static/home.js", "rb").read()
    assert response.headers["Cache-Control"] == "public, max-age=31536000, immutable"
    # Ancienne empreinte : contenu actuel, mais pas figé un an chez le visiteur.
    stale = client.get("/static/home.js?v=0000000000", headers={"Accept-Encoding": "gzip"})
    assert stale.headers["Cache-Control"] == "public, max-age=3600"
    # Les requêtes partielles restent non compressées et correctes.
    partial = client.get(url, headers={"Accept-Encoding": "gzip", "Range": "bytes=0-9"})
    assert partial.status_code == 206 and "Content-Encoding" not in partial.headers


def test_home_page_scripts_use_cacheable_asset_versions():
    import os
    import re

    os.environ.setdefault("OPENAI_API_KEY", "test-key")
    from app import app
    from services.site_layout import asset_url

    html = app.test_client().get("/").get_data(as_text=True)
    assert asset_url("home.js") in html and asset_url("theme.js") in html
    for src in re.findall(r'src="(/static/[^"]+)"', html):
        cached = app.test_client().get(src)
        assert cached.headers["Cache-Control"] == "public, max-age=31536000, immutable", src
