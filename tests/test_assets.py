from services.assets import ICON_SVG, OG_SVG, build_icon_png, build_og_png


def test_svg_assets_are_self_contained():
    assert ICON_SVG.startswith("<svg")
    assert "Teranga AI" in OG_SVG


def test_icon_png_has_requested_dimensions():
    from PIL import Image
    from io import BytesIO

    image = Image.open(BytesIO(build_icon_png(192)))
    assert image.size == (192, 192)
    assert image.format == "PNG"


def test_og_png_has_requested_dimensions():
    from PIL import Image
    from io import BytesIO

    image = Image.open(BytesIO(build_og_png()))
    assert image.size == (1200, 630)
    assert image.format == "PNG"


def test_shared_images_referenced_by_pages_are_served():
    import io
    import os

    os.environ.setdefault("OPENAI_API_KEY", "test-key")
    from PIL import Image

    from app import app

    client = app.test_client()
    og = client.get("/og.png")
    assert og.status_code == 200 and og.mimetype == "image/png"
    assert Image.open(io.BytesIO(og.data)).size == (1200, 630)
    assert og.headers["Cache-Control"] == "public, max-age=86400"
    for path, mimetype in (("/icon.svg", "image/svg+xml"), ("/og.svg", "image/svg+xml"), ("/favicon.ico", "image/png")):
        response = client.get(path)
        assert response.status_code == 200, path
        assert response.mimetype == mimetype
        assert response.headers["Cache-Control"] == "public, max-age=86400", path
