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
