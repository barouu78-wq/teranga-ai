"""Documents commerciaux : le modèle de suivi exige une source datée, le plan n'invente aucun contact."""

import csv
import re
from pathlib import Path

DOCS = Path(__file__).resolve().parent.parent / "docs"
PLAN = DOCS / "AGENT-COMMERCIAL-30-JOURS.md"
TEMPLATE = DOCS / "prospection_modele.csv"


def test_modele_de_prospection_exige_source_et_date():
    with TEMPLATE.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.reader(handle))
    header = rows[0]
    for column in ("segment", "source_url", "date_verification", "score", "contact_public", "statut"):
        assert column in header
    assert len(header) == len(set(header))


def test_modele_de_prospection_reste_vide():
    # Le modèle versionné ne contient aucune donnée de prospect (données personnelles hors du dépôt).
    with TEMPLATE.open(encoding="utf-8", newline="") as handle:
        rows = [row for row in csv.reader(handle) if any(cell.strip() for cell in row)]
    assert len(rows) == 1


def test_plan_commercial_sans_coordonnees_inventees():
    text = PLAN.read_text(encoding="utf-8")
    assert not re.search(r"[\w.+-]+@[\w-]+\.[a-z]{2,}", text, re.I), "aucune adresse e-mail dans le plan"
    assert not re.search(r"(?:\+?\d[ .]?){8,}", text), "aucun numéro de téléphone dans le plan"


def test_plan_commercial_marque_les_prix_comme_hypotheses():
    text = PLAN.read_text(encoding="utf-8")
    prices = [line for line in text.splitlines() if "FCFA" in line]
    assert prices
    for line in prices:
        assert "hypothèse" in line.lower() and "non validée" in line, line
    assert "non validées par le marché" in text
