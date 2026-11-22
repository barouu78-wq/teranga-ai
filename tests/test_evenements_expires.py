"""Ticket « événements expirés » (audit du 22 novembre 2026) : les JOJ Dakar 2026 (31 octobre – 13 novembre) restaient
annoncés après la clôture.

Dans un navigateur, la carte de l'accueil disparaissait bien le 14 novembre (date du visiteur, static/theme.js), mais
son texte (« Jeux Olympiques de la Jeunesse · Dakar 2026 · 31 oct. – 13 nov. ») restait dans la page envoyée à tous,
caché seulement par la feuille de style : un outil d'audit, un moteur de recherche ou un lecteur sans feuille de style
le voyait encore. La carte vit maintenant dans un <template>, ajouté à la page par home.js pendant les Jeux seulement.
"""

import datetime as dt
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from app import app
from services import events
from services.seo import render_seo_page

ROOT = Path(__file__).resolve().parents[1]
THEME_JS = ROOT / "static" / "theme.js"


def _texte_visible(html):
    """Texte de la page hors <style>, <script> et <template> (contenu inerte, jamais affiché tel quel)."""
    return re.sub(r"<style.*?</style>|<script.*?</script>|<template.*?</template>", "", html, flags=re.S)


def test_l_accueil_n_envoie_plus_le_texte_des_jeux():
    html = app.test_client().get("/").get_data(as_text=True)
    visible = _texte_visible(html)
    assert "Jeux Olympiques" not in visible and "JOJ" not in visible and "13 nov." not in visible
    # La carte reste disponible pour home.js, dans un modèle inerte, avec son lien vers le guide.
    modele = re.search(r'<template id="jojCardTpl">(.*?)</template>', html, re.S)
    assert modele and 'id="jojCard"' in modele.group(1) and 'href="/joj-dakar-2026"' in modele.group(1)


def _joj():
    (event,) = [e for e in events.EVENTS if e[2].startswith("Jeux Olympiques de la Jeunesse")]
    return event[0], event[1]


def test_les_dates_des_jeux_du_theme_suivent_le_calendrier():
    """Une seule vérité : static/theme.js (accueil) et services/events.py (calendrier, IA, guide) disent les mêmes
    dates. home.js lit celles du thème au lieu d'en garder une copie."""
    start, end = _joj()
    bloc = re.search(r"joj:\[(\d+),(\d+),(\d+)\]", THEME_JS.read_text(encoding="utf-8"))
    assert bloc, "joj introuvable dans le tableau FETES de static/theme.js"
    month, day, days = map(int, bloc.groups())
    assert (month, day) == (start.month, start.day)
    assert days == (end - start).days + 1  # 14 jours, 13 novembre inclus
    home_js = (ROOT / "static" / "home.js").read_text(encoding="utf-8")
    assert "new Date(2026,9,31)" not in home_js and "JOJ_DAYS=14" not in home_js


@pytest.mark.parametrize("today,shown", [
    (dt.date(2026, 10, 30), True),   # à venir : annoncé (calendrier, IA)
    (dt.date(2026, 10, 31), True),   # premier jour
    (dt.date(2026, 11, 13), True),   # dernier jour, inclus
    (dt.date(2026, 11, 14), False),  # terminé
    (dt.date(2026, 11, 22), False),  # jour de l'audit
])
def test_le_calendrier_retire_un_evenement_termine(today, shown):
    noms = [e["name"] for e in events.upcoming_events(today)]
    assert any(n.startswith("Jeux Olympiques de la Jeunesse") for n in noms) is shown


def test_un_evenement_a_la_date_invalide_n_est_jamais_affiche(monkeypatch):
    """Une ligne mal saisie (date absente, texte, fin avant le début) est ignorée au lieu de faire planter la page."""
    monkeypatch.setattr(events, "EVENTS", events.EVENTS + (
        (None, None, "Sans date", "Dakar", "festival", True, ""),
        ("2026-12-01", None, "Date en texte", "Dakar", "festival", True, ""),
        (dt.date(2026, 12, 10), dt.date(2026, 12, 1), "Fin avant début", "Dakar", "festival", True, ""),
    ))
    noms = [e["name"] for e in events.upcoming_events(dt.date(2026, 11, 22))]
    assert "Noël" in noms
    assert not {"Sans date", "Date en texte", "Fin avant début"} & set(noms)
    assert "Sans date" not in events.events_context(dt.date(2026, 11, 22))


@pytest.mark.parametrize("today,past", [(dt.date(2026, 11, 13), False), (dt.date(2026, 11, 14), True)])
def test_le_guide_des_jeux_passe_au_passe_apres_la_cloture(monkeypatch, today, past):
    monkeypatch.setattr(events, "today_in_dakar", lambda: today)
    page = render_seo_page("joj-dakar-2026", "https://teranga-ai.fr").get_data(as_text=True)
    assert ("Les JOJ Dakar 2026 sont terminés" in page) is past
    assert ("ont eu lieu du 31 octobre au 13 novembre 2026" in page) is past
    assert ("ont lieu du 31 octobre au 13 novembre 2026" in page) is not past
    assert ("Le programme du jour" in page) is not past  # plus de programme ni de billets à chercher


def test_la_date_de_dakar_est_l_heure_universelle():
    """Dakar vit à l'heure universelle toute l'année (pas d'heure d'été) : la date ne dépend pas du serveur."""
    assert events.today_in_dakar() == dt.datetime.now(dt.timezone.utc).date()


# Le choix de la fête se fait dans le navigateur (date du visiteur). On exécute le vrai static/theme.js dans Node.
_NODE = r"""
const fs = require('fs');
const src = fs.readFileSync(process.argv[2], 'utf8');
const store = {};
global.localStorage = {getItem: k => store[k] ?? null, setItem: (k, v) => { store[k] = String(v); }, removeItem: k => { delete store[k]; }};
global.location = {search: ''};
global.document = {documentElement: {dataset: {}}};
global.window = global;
global.setInterval = () => 0;
eval(src);
const t = window.terangaTheme;
const out = {};
for (const [k, y, m, d, h] of JSON.parse(process.argv[3])) out[k] = t.fete(new Date(y, m - 1, d, h, 0));
out.range = t.range('joj', 2026);
out.none = t.range('joj', 2027);
out.bad = t.range('inconnue', 2026);
console.log(JSON.stringify(out));
"""


@pytest.mark.skipif(shutil.which("node") is None, reason="node absent")
def test_le_theme_choisit_la_fete_selon_la_date_du_visiteur(tmp_path):
    script = tmp_path / "fete.js"
    script.write_text(_NODE, encoding="utf-8")
    cas = [["avant", 2026, 10, 30, 23], ["debut", 2026, 10, 31, 0], ["fin", 2026, 11, 13, 23],
           ["apres", 2026, 11, 14, 0], ["audit", 2026, 11, 22, 10], ["noel", 2026, 12, 25, 12]]
    sortie = subprocess.run(["node", str(script), str(THEME_JS), json.dumps(cas)],
                            capture_output=True, text=True, check=True, timeout=30)
    out = json.loads(sortie.stdout)
    assert (out["avant"], out["debut"], out["fin"], out["apres"], out["audit"]) == ("", "joj", "joj", "", "")
    assert out["range"] == {"start": [2026, 10, 31], "days": 14}
    assert out["none"] is None and out["bad"] is None
