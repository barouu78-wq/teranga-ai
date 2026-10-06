"""La fiche Google Play respecte les limites de caractères de la Play Console."""

import re
from pathlib import Path

from PIL import Image

DIR = Path(__file__).resolve().parents[1] / "docs" / "google-play"
TEXT = (DIR / "FICHE-GOOGLE-PLAY.md").read_text(encoding="utf-8")


def _block(title):
    after = TEXT.split(title, 1)[1]
    return re.search(r"```\n(.*?)\n```", after, re.S).group(1)


def test_listing_texts_fit_play_console_limits():
    assert len(_block("**Nom de l'application**")) <= 30
    assert len(_block("**Description courte**")) <= 80
    assert len(_block("**Short description**")) <= 80
    assert len(_block("**Description complète**")) <= 4000
    assert len(_block("**Full description**")) <= 4000


def test_store_graphics_have_required_sizes():
    assert Image.open(DIR / "image-de-presentation-1024x500.png").size == (1024, 500)
    for shot in sorted(DIR.glob("capture-*.png")):
        width, height = Image.open(shot).size
        # La Play Console demande un rapport 9:16 exact pour les captures de téléphone.
        assert (width, height) == (1080, 1920), shot.name
