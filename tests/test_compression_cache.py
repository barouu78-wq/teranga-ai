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
