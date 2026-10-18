"""Prix de l'adresse partenaire : décision 1 du plan « Teranga AI — plan de A à Z », prise le 18 octobre 2026.

Un seul prix, simple, en FCFA : premier mois offert, puis 15 000 FCFA par mois, sans engagement. Il est affiché sur
/offres-partenaires et repris tel quel dans les messages prêts à envoyer, pour qu'un prospect lise partout le même
montant.
"""

import os
from pathlib import Path

os.environ.setdefault("OPENAI_API_KEY", "test-key")

from routes.monetization import PARTNER_MONTHLY_PRICE, render_offers_page  # noqa: E402

DOCS = Path(__file__).resolve().parent.parent / "docs"


def test_le_prix_decide_est_15_000_fcfa():
    assert PARTNER_MONTHLY_PRICE == "15 000 FCFA"


def test_la_page_des_offres_affiche_le_prix_et_le_mois_offert():
    html = render_offers_page()
    assert "premier mois offert" in html.lower()
    assert f"{PARTNER_MONTHLY_PRICE} par mois" in html
    assert "sans engagement" in html
    # Plus de « tarifs sur demande » pour l'adresse partenaire : le prix est public.
    assert "Tarifs de lancement sur demande" not in html


def test_les_messages_prets_donnent_le_meme_prix_sans_trou_a_remplir():
    for name in ("VENTES-MESSAGES.md", "messages-prospects-prets.md"):
        text = (DOCS / name).read_text(encoding="utf-8")
        assert "[prix]" not in text and "[ton prix" not in text, name
        assert "15 000 FCFA par mois" in text.replace(" ", " "), name
