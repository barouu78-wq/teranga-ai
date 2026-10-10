"""Le lieu demandé ne doit jamais être remplacé par un autre lieu dans la recherche d'images.

Ces tests suivent le vrai chemin du chat (`app.fetch_topic_images`, base de connaissances
réelle) avec des fournisseurs simulés qui ne renvoient rien : toutes les requêtes que
Teranga enverrait à Google, Wikipédia et Commons sont enregistrées, puis vérifiées.
Aucun appel réseau.
"""

import io
import json
import os
import unicodedata

import pytest

os.environ.setdefault("OPENAI_API_KEY", "test-key")


def _norm(value):
    text = unicodedata.normalize("NFD", str(value or "").lower())
    return "".join(ch for ch in text if unicodedata.category(ch) != "Mn")


@pytest.fixture
def requetes(monkeypatch):
    """Enregistre chaque requête d'image que le chat enverrait (aucun résultat renvoyé)."""
    import app as app_module
    import services.image_topics as image_topics

    image_topics._TOPIC_IMAGE_CACHE.clear()
    journal = {"google": [], "article": [], "commons": [], "city": []}

    def fake(source):
        def call(title, limit=4):
            journal[source].append(title)
            return []
        return call

    monkeypatch.setattr(app_module, "fetch_google_images", fake("google"))
    monkeypatch.setattr(app_module, "fetch_article_images", fake("article"))
    monkeypatch.setattr(app_module, "fetch_commons_images", fake("commons"))
    monkeypatch.setattr(app_module, "fetch_city_image", lambda title: journal["city"].append(title))

    def demander(message):
        image_topics._TOPIC_IMAGE_CACHE.clear()
        for liste in journal.values():
            liste.clear()
        app_module.fetch_topic_images(message)
        return {source: list(valeurs) for source, valeurs in journal.items()}

    yield demander
    image_topics._TOPIC_IMAGE_CACHE.clear()


def _toutes(journal):
    return [_norm(titre) for valeurs in journal.values() for titre in valeurs]


# ---------------------------------------------------------------------------
# Dakar / Saly / Gorée : le lieu demandé reste le seul lieu cherché
# ---------------------------------------------------------------------------

def test_demande_dakar_ne_cherche_aucun_autre_lieu(requetes):
    journal = requetes("Montre-moi des photos de Dakar")
    assert journal["google"] == ["Dakar"]
    # Avant : les articles Wikipédia de Gorée et les recherches Commons de Rufisque
    # et Pikine complétaient la galerie de Dakar.
    for autre in ("goree", "rufisque", "pikine", "saly", "mbour"):
        assert not any(autre in titre for titre in _toutes(journal)), (autre, journal)


def test_demande_saly_ne_cherche_pas_dakar(requetes):
    journal = requetes("photos de la plage de Saly")
    assert _norm(journal["google"][0]).startswith("saly")
    assert not any("dakar" in titre for titre in _toutes(journal)), journal


def test_demande_goree_ne_cherche_pas_dakar(requetes):
    journal = requetes("montre-moi des photos de l'île de Gorée")
    assert "goree" in _norm(journal["google"][0])
    assert not any("dakar" in titre for titre in _toutes(journal)), journal


# ---------------------------------------------------------------------------
# Lieux de la région absents de la liste des lieux : jamais remplacés par la région
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("demande,attendu", [
    ("photos de Pikine", "pikine"),
    ("photos de Guédiawaye", "guediawaye"),
    ("photos de Yoff", "yoff"),
    ("photos de Rufisque", "rufisque"),
    ("photos de la Médina", "medina"),
    ("photos de Nianing", "nianing"),
    ("photos de Foundiougne", "foundiougne"),
])
def test_sous_localite_de_region_garde_son_nom(requetes, demande, attendu):
    journal = requetes(demande)
    premiere = _norm(journal["google"][0])
    assert attendu in premiere, journal
    # Ni la région entière, ni un voisin de la même région.
    for region_ou_voisin in ("dakar", "thies", "fatick", "mbour", "saly", "tivaouane", "sokone"):
        assert region_ou_voisin not in premiere, journal
    assert not any(v in titre for titre in _toutes(journal) for v in ("goree", "saly", "tivaouane", "sokone")), journal


@pytest.mark.parametrize("demande,attendu", [
    ("photos de plages", "plages Sénégal"),
    ("photos de savane", "savane Sénégal"),
    ("photos de mangroves", "mangroves Sénégal"),
])
def test_theme_generique_reste_une_recherche_libre(requetes, demande, attendu):
    # Avant : « plages » (mot de la région Ziguinchor) renvoyait Ziguinchor, « savane »
    # Tambacounda… Un nom commun n'est ni un lieu ni un article Wikipédia du monde entier.
    journal = requetes(demande)
    assert journal["google"] == [attendu]
    assert journal["article"] == []
    for region in ("ziguinchor", "tambacounda", "fatick", "sedhiou", "oussouye"):
        assert not any(region in titre for titre in _toutes(journal)), journal


def test_titres_de_la_base_pour_dakar_et_pikine():
    from app import knowledge_image_titles

    assert knowledge_image_titles("montre moi les photos de Dakar") == ["Dakar"]
    # Un lieu de la région est précisé par « Sénégal » (comme les requêtes de la base).
    assert knowledge_image_titles("montre moi les photos de Pikine") == ["Pikine Sénégal"]


# ---------------------------------------------------------------------------
# Alias et accents
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("demande,attendu", [
    ("photos de Gorée", "Île de Gorée Sénégal"),
    ("photos de Goree", "Île de Gorée Sénégal"),
    ("photos de Goree Island", "Île de Gorée Sénégal"),
    ("photos de l'île de Gorée", "Île de Gorée Sénégal"),
    ("photos de Saint-Louis", "Île Saint-Louis Sénégal"),
    ("photos de St Louis", "Île Saint-Louis Sénégal"),
    ("photos de St-Louis", "Île Saint-Louis Sénégal"),
    ("photos de Saint Louis", "Île Saint-Louis Sénégal"),
    ("photos du Lac Rose", "Lac Rose Sénégal"),
    ("photos du Pink Lake", "Lac Rose Sénégal"),
    ("photos du Marché Sandaga", "Marché Sandaga Dakar"),
    ("photos de Mbour", "Mbour Sénégal"),
    ("photos de Joal-Fadiouth", "Joal-Fadiouth Sénégal"),
    ("photos de Joal Fadiouth", "Joal-Fadiouth Sénégal"),
    ("photos de Ziguinchor", "Ziguinchor Sénégal"),
])
def test_alias_et_accents_donnent_le_meme_lieu(requetes, demande, attendu):
    assert requetes(demande)["google"][0] == attendu


# ---------------------------------------------------------------------------
# Un lieu voisin cité dans la même phrase ne prend pas le dessus
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("demande,voulu,voisin", [
    ("photos de Dakar et pas de Saly", "dakar", "saly"),
    ("photos de Saly, pas de Dakar", "saly", "dakar"),
    ("photos de Saly près de Mbour", "saly", "mbour"),
    ("photos de Mbour près de Saly", "mbour", "saly"),
    ("photos de Dakar près de Gorée", "dakar", "goree"),
    ("photos de Gorée depuis Dakar", "goree", "dakar"),
    ("photos du Lac Rose près de Dakar", "lac rose", "dakar"),
    ("photos de Saint-Louis loin de Dakar", "saint-louis", "dakar"),
    ("Show me Saly, not Dakar", "saly", "dakar"),
])
def test_lieu_voisin_ne_prend_pas_le_dessus(requetes, demande, voulu, voisin):
    journal = requetes(demande)
    assert voulu in _norm(journal["google"][0]), journal
    assert not any(voisin in titre for titre in _toutes(journal)), journal


def test_deux_lieux_demandes_suivent_l_ordre_de_la_phrase(requetes):
    # Avant : l'ordre du fichier de données décidait (Mbour avant Saly).
    assert _norm(requetes("photos de Saly et de Mbour")["google"][0]).startswith("saly")
    assert _norm(requetes("photos de Mbour et de Saly")["google"][0]).startswith("mbour")


def test_lieu_unique_apres_un_marqueur_reste_le_lieu_demande(requetes):
    # « près de Saly » est le seul lieu cité : on ne le perd pas.
    assert _norm(requetes("photos près de Saly")["google"][0]).startswith("saly")
    assert _norm(requetes("montre-moi des photos depuis Dakar")["google"][0]).startswith("dakar")


# ---------------------------------------------------------------------------
# Cache : une demande ne reçoit jamais la galerie d'un autre lieu
# ---------------------------------------------------------------------------

def test_cache_ne_melange_pas_dakar_et_pikine(monkeypatch):
    import app as app_module
    import services.image_topics as image_topics

    image_topics._TOPIC_IMAGE_CACHE.clear()
    appels = []

    def google(title, limit=4):
        appels.append(title)
        return [{"url": f"https://upload.wikimedia.org/{_norm(title).replace(' ', '_')}.jpg", "alt": title}]

    monkeypatch.setattr(app_module, "fetch_google_images", google)
    monkeypatch.setattr(app_module, "fetch_article_images", lambda title, limit=6: [])
    monkeypatch.setattr(app_module, "fetch_commons_images", lambda title, limit=4: [])
    monkeypatch.setattr(app_module, "fetch_city_image", lambda title: None)

    dakar = app_module.fetch_topic_images("photos de Dakar")
    pikine = app_module.fetch_topic_images("photos de Pikine")
    assert [p["url"] for p in dakar] != [p["url"] for p in pikine]
    assert "pikine" in pikine[0]["url"] and "dakar" not in pikine[0]["url"]
    assert len(appels) == 2
    image_topics._TOPIC_IMAGE_CACHE.clear()


# ---------------------------------------------------------------------------
# Classement Google : la photo du lieu précis passe avant la photo de la ville
# ---------------------------------------------------------------------------

def _google(requete, elements):
    from services.images import fetch_google_images

    corps = {"items": [
        {"title": titre, "link": "https://img.example/" + titre.replace(" ", "_") + ".jpg",
         "image": {"thumbnailLink": "https://encrypted-tbn0.gstatic.com/" + titre.replace(" ", "_"),
                   "contextLink": page}}
        for titre, page in elements
    ]}
    photos = fetch_google_images(requete, "k", "cx", limit=4,
                                 urlopen_fn=lambda req, timeout=8: io.BytesIO(json.dumps(corps).encode()))
    return [p["alt"] for p in photos]


@pytest.mark.parametrize("requete,lieu,page", [
    ("Marché Sandaga Dakar", "Marché Sandaga", "https://example.com/sandaga-market"),
    ("Monument Renaissance africaine Dakar", "Monument de la Renaissance africaine", "https://example.com/monument"),
    ("Pointe des Almadies Dakar", "Pointe des Almadies", "https://example.com/almadies"),
    ("Musée Civilisations Noires Dakar", "Musée des Civilisations Noires", "https://example.com/mcn"),
])
def test_photo_du_lieu_precis_n_est_pas_ecartee_par_une_photo_de_la_ville(requete, lieu, page):
    photos = _google(requete, [
        ("Dakar skyline at night", "https://example.com/dakar-skyline"),
        (lieu, page),
        ("Plateau Dakar vue aérienne", "https://example.com/plateau-dakar"),
    ])
    # Avant : la photo du lieu (sans le mot « Dakar ») était éliminée et seules
    # des photos générales de Dakar restaient.
    assert lieu in photos
    assert photos[0] == lieu


def test_google_reconnait_st_louis_comme_saint_louis():
    # « St Louis » est un lieu précis comme « Saint-Louis » : une photo d'une autre ville
    # sans lien avec lui est écartée.
    photos = _google("St Louis Sénégal", [
        ("Dakar skyline at night", "https://example.com/dakar-skyline"),
        ("St Louis du Sénégal, pirogues", "https://example.com/st-louis-pirogues"),
    ])
    assert photos == ["St Louis du Sénégal, pirogues"]


def test_ville_seule_garde_son_classement():
    # Sans lieu précis dans la requête, comportement inchangé : Dakar avant Saly.
    photos = _google("Dakar", [
        ("Plage de Saly", "https://www.flickr.com/photos/x/2"),
        ("Corniche de Dakar", "https://commons.wikimedia.org/wiki/Corniche"),
        ("Belle plage du Sénégal", "https://example.com/senegal"),
    ])
    assert photos == ["Corniche de Dakar"]


# ---------------------------------------------------------------------------
# « Oui » après une proposition de photos : le sujet est celui de l'échange en cours
# ---------------------------------------------------------------------------

def test_oui_apres_un_changement_de_lieu_montre_le_nouveau_lieu():
    from services.chat_payload_service import photo_request

    historique = [
        {"role": "user", "content": "montre moi des photos de Saly"},
        {"role": "assistant", "content": "Voici quelques photos pour « Saly »."},
        {"role": "user", "content": "Parle-moi de Dakar"},
        {"role": "assistant", "content": "Dakar est la capitale. Veux-tu voir des photos de Dakar ?"},
        {"role": "user", "content": "oui"},
    ]
    assert photo_request("oui", historique) == (True, "photos : Parle-moi de Dakar")


def test_oui_garde_le_lieu_des_photos_si_la_question_n_en_nomme_pas():
    from services.chat_payload_service import photo_request

    historique = [
        {"role": "user", "content": "montre moi des photos de Saly"},
        {"role": "assistant", "content": "Voici quelques photos pour « Saly »."},
        {"role": "user", "content": "Quel est le meilleur mois ?"},
        {"role": "assistant", "content": "Novembre à avril. Veux-tu d'autres photos ?"},
        {"role": "user", "content": "oui"},
    ]
    assert photo_request("oui", historique) == (True, "montre moi des photos de Saly")


# ---------------------------------------------------------------------------
# Briques : graphies, ordre de la phrase, lieux de repère
# ---------------------------------------------------------------------------

def test_graphies_equivalentes_d_un_meme_lieu():
    from services.photo_search import fold_place_text, term_position

    assert fold_place_text("St-Louis") == fold_place_text("Saint Louis") == "saint louis"
    assert fold_place_text("Ste Marie") == "sainte marie"
    assert fold_place_text("Joal–Fadiouth") == "joal fadiouth"
    assert term_position("photos de GORÉE", "Goree") == term_position("photos de goree", "Gorée") == 10
    # Mot entier : « touba » n'est pas dans « Toubab Dialaw ».
    assert term_position("photos de Toubab Dialaw", "Touba") is None
    assert term_position("photos", "") is None


def test_sujets_wikipedia_dans_l_ordre_de_la_phrase():
    from services.images import topic_wikipedia_titles

    # Avant : l'ordre du tableau décidait (M'Bour avant Saly Portudal).
    assert topic_wikipedia_titles("photos de Saly et de Mbour", 4) == ["Saly Portudal", "M'Bour"]
    assert topic_wikipedia_titles("photos de Mbour et de Saly", 4) == ["M'Bour", "Saly Portudal"]
    assert topic_wikipedia_titles("photos de Saly et de Mbour", 1) == ["Saly Portudal"]


def test_lieux_de_repere_sont_retires_de_la_demande():
    from services.image_topics import _focus_clause

    assert _focus_clause("photos de Saly près de Mbour") == "photos de Saly"
    assert _focus_clause("photos de Dakar et pas de Saly") == "photos de Dakar et"
    assert _focus_clause("photos de plage, pas Saly mais Mbour") == "photos de plage, mais Mbour"
    assert _focus_clause("Show me Saly, not Dakar") == "Show me Saly,"
    assert _focus_clause("photos d'Abéné à côté d'Elinkine") == "photos d'Abéné"
    # « à partir de » n'est pas « à part » ; une phrase sans repère reste intacte.
    assert _focus_clause("photos de Dakar à partir de Rufisque") == "photos de Dakar"
    assert _focus_clause("photos  de   Dakar") == "photos de Dakar"
    assert _focus_clause(None) == ""
    # Un caractère qui change de longueur une fois mis en minuscules ne décale rien.
    assert _focus_clause("İstanbul près de Dakar") == "İstanbul"


def test_goree_absente_de_la_base_reste_reconnue():
    from services.image_topics import _specific_place_titles

    assert _specific_place_titles("photos de Gorée", {"places": []}, _norm) == ["Île de Gorée"]
    # Gorée présente dans la base : aucune requête en double.
    base = {"places": [{"name": "Île de Gorée", "image_queries": ["Île de Gorée Sénégal"]}]}
    assert _specific_place_titles("photos de Gorée", base, _norm) == ["Île de Gorée Sénégal"]
