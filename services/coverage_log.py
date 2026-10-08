"""Journal des lacunes : sur quels sujets l'IA n'a rien reçu de fiable, sans rien retenir de ce que disent les gens.

Pour chaque question du chat, le journal détermine
  (a) un ou plusieurs « thèmes » parmi un vocabulaire FIXE et FERMÉ (THEMES, ci-dessous) ;
  (b) si, pour ce thème, le contexte envoyé à l'IA contenait quelque chose : un repère pratique vérifié, un lieu,
      un plat, une fête ou une météo de la base, ou une recherche web.
Il ajoute ensuite 1 à des compteurs « par jour et par thème » (couvert / non couvert), et rien d'autre.

Ce qui n'est JAMAIS conservé : le texte de la question, l'adresse IP, l'identifiant du visiteur, ni un
hachage de l'un d'eux. Les clés Redis sont « teranga:coverage:AAAA-MM-JJ » et les champs sont
« total » ou « <thème>|c » / « <thème>|n », où <thème> vient obligatoirement du vocabulaire ci-dessous :
une valeur saisie par un visiteur ne peut donc jamais devenir une clé. Les combinaisons de thèmes d'une même
question ne sont pas conservées non plus (chaque thème est compté à part). Durée de vie : 90 jours.

Même modèle que services/click_stats.py : Redis s'il est disponible (compteurs partagés entre les workers),
sinon la mémoire du processus. L'écriture Redis se fait dans un fil à part : une panne ou une lenteur de Redis
ne retarde jamais la réponse du chat, et toute erreur du journal est avalée.
"""

from __future__ import annotations

import datetime as _dt
import re
import threading
from collections import Counter
from typing import NamedTuple

from services.places import mentioned_places
from services.practical_facts import matching_topics
from services.senegal_knowledge import REGION_ALIASES
from services.text import fold_text

_PREFIX = "teranga:coverage:"
KEEP_DAYS = 90
_KEEP_SECONDS = KEEP_DAYS * 24 * 3600
OTHER = "autre"


class Theme(NamedTuple):
    id: str
    label: str
    keywords: tuple[str, ...]
    covers: frozenset[str]


def _theme(theme_id: str, label: str, keywords: str, covers: str = "") -> Theme:
    return Theme(
        theme_id, label,
        tuple(k.strip() for k in keywords.split(",") if k.strip()),
        frozenset(c.strip() for c in covers.split() if c.strip()),
    )


# Vocabulaire FERMÉ. Mots-clés sans accents (comparés au texte passé par fold_text) ; « mot* » accepte toute fin de
# mot, « re:… » est une expression régulière brute. Un mot simple est cherché en mot entier (« prise » ne se
# trouve pas dans « entreprise »), avec pluriel en s/x.
# « covers » : ce qui, dans le contexte de l'IA, couvre ce thème. « repere:<id> » = repère pratique vérifié
# (services/practical_facts.py) ; les autres signaux viennent de la base de connaissances (voir _MARKERS).
# Une recherche web déclenchée couvre n'importe quel thème (voir covered()).
THEMES: tuple[Theme, ...] = (
    _theme("sante", "Santé",
           "sante, malade*, maladie*, medecin*, docteur*, hopital, hopitaux, clinique*, pharmacie*, medicament*, vaccin*, "
           "paludisme, palu, malaria, fievre*, dentiste*, grossesse, enceinte, accouchement, ordonnance*, diabete, "
           "hypertension, infirmier*, soin, symptome*, health, doctor, hospital, pharmacy",
           "repere:sante repere:urgences repere:protection"),
    _theme("urgences", "Urgences et sécurité",
           "urgence*, police, policier*, gendarmerie, pompier*, samu, secours, accident*, agression*, agresse*, arnaque*, "
           "danger*, dangereux, re:securite(?! sociale| familiale| alimentaire), perdu*, vole, voleur*, re:victime d un vol, "
           "emergenc*, safety",
           "repere:urgences"),
    _theme("papiers", "Papiers et démarches",
           "papiers, demarche*, administration*, carte d identite, cni, carte biometrique, acte de naissance, "
           "extrait de naissance, etat civil, casier judiciaire, legalisation, certificat*, mairie*, prefecture*, "
           "consulat*, ambassade*, nationalite, permis de conduire, carte grise, naturalisation, e senegal, "
           "jugement suppletif, passeport senegalais, re:(?:renouvel\\w*|refaire|duplicata|perdu|perte) (?:\\w+ )?(?:\\w+ )?passeport",
           "repere:papiers"),
    _theme("visa", "Visa et entrée dans le pays",
           "visa*, passeport, passport, formalites, douane*, entrer au senegal, entree au senegal, frontiere*, "
           "titre de sejour, carte de sejour, permis de sejour, entry requirements, customs",
           "repere:visa"),
    _theme("argent", "Argent, change et paiements",
           "argent, euro*, fcfa, cfa, xof, change, changer de l argent, dollar*, payer, paiement*, wave, orange money, "
           "mobile money, carte bancaire, retrait*, distributeur*, atm, banque*, bancaire*, virement*, western union, "
           "transfert d argent, envoyer de l argent, monnaie, espece*, pourboire*, money, cash, payment",
           "repere:argent"),
    _theme("transport", "Transport et déplacements",
           "taxi*, sept places, 7 places, ter, brt, bus, car rapide, dem dikk, aibd, aeroport*, airport, ferry, chaloupe, "
           "bateau*, train, voiture*, location de voiture, louer une voiture, conduire, conduite, se deplacer, "
           "deplacement*, comment aller, trajet*, route*, autoroute*, peage*, moto*, jakarta, vtc, uber, yango, "
           "covoiturage, navette*, avion*, air senegal, flight*, compagnie aerienne, transport*, get around, billet*, "
           "re:(?:reserver|prendre|trouver|chercher) (?:un |des |mon |mes )?vols?, re:vols? (?:pour|vers|depuis|direct|retour|paris|dakar|air)",
           "repere:transport"),
    _theme("logement", "Logement, location et immobilier",
           "logement*, loyer*, colocation*, immobilier, appartement*, villa*, studio*, terrain*, parcelle*, titre foncier, "
           "foncier*, cadastre, bail, acheter une maison, construire une maison, proprietaire*, caution, agent immobilier, "
           "real estate, apartment*, re:locations? (?:d |de |du )?(?:appartement|maison|chambre|villa|studio|logement), "
           "re:(?:louer|loue) (?:un |une |mon |ma )?(?:appartement|maison|chambre|villa|studio)",
           "repere:foncier"),
    _theme("hebergement", "Hôtels et hébergement",
           "hotel*, auberge*, hebergement*, gite*, campement*, ou dormir, dormir, airbnb, booking, chambre d hote, "
           "lodge*, resort*, accommodation, where to stay",
           "partenaires"),
    _theme("emploi", "Emploi et travail",
           "emploi*, travail, travailler, recrutement*, recrute*, embauche*, cv, lettre de motivation, salaire*, stage*, "
           "stagiaire*, chomage, chomeur*, job*, concours, fonction publique, metier*, freelance*, carriere*, "
           "employeur*, employe*, contrat de travail, licenci*, demission*",
           ""),
    _theme("etudes", "Études et formation",
           "etude*, etudier, etudiant*, universite*, fac, ucad, campusen, bac, bachelier*, bfem, licence, master, "
           "doctorat, bourse*, ecole*, college*, lycee*, creche*, scolarite, formation*, diplome*, inscription*, "
           "orientation, enseignant*, professeur*, coud, isep, student*, school, university",
           "repere:etudes"),
    _theme("entreprise", "Créer une entreprise",
           "entreprise*, creer une societe, ouvrir une societe, creation de societe, startup*, start up, ninea, rccm, apix, "
           "immatriculation, statut juridique, sarl, suarl, gie, auto entrepreneur, entrepreneur*, entreprendre, "
           "business, financement*, patente, impot*, fiscal*, tva",
           "repere:entreprise"),
    _theme("commerce", "Commerce et vente",
           "vendre, vente*, vendeur*, client*, boutique*, commerce*, commercant*, grossiste*, fournisseur*, marge*, "
           "prix de vente, stock*, livraison*, importer, exporter, whatsapp business, e commerce, revendre, sell, customers",
           "repere:vente"),
    _theme("agriculture", "Agriculture et élevage",
           "agricult*, agriculteur*, cultiver, champ, champs, recolte*, semence*, engrais, irrigation, arachide*, sorgho, "
           "maraichage, horticulture, anacarde, cajou, elevage, eleveur*, betail, vache*, bovin*, mouton*, chevre*, "
           "volaille*, poulailler*, ferme, fermes, paysan*, tracteur*, agro*, farming, crop*",
           ""),
    _theme("peche", "Pêche et produits de la mer",
           "peche*, pecheur*, pirogue*, mareyeur*, aquaculture, quai de peche, thon, sardinelle*, huitre*, fishing, "
           "fisherman, fish market, marche aux poissons",
           "cite lieux"),
    _theme("voyage", "Voyage et tourisme",
           "voyage*, voyager, sejour*, visiter, visite*, tourisme, touriste*, tourist*, itineraire*, circuit*, excursion*, "
           "que voir, quoi voir, a voir, vacances, plage*, week end, weekend, decalage horaire, fuseau horaire, "
           "quelle heure, time zone, trip, travel*, holiday*, sightseeing, agence de voyage, decouvrir, decouverte",
           "cite guide repere:saison repere:heure repere:visa"),
    _theme("meteo", "Météo et saisons",
           "meteo, quel temps, pluie*, pleut, pleuvoir, temperature*, chaleur, saison*, hivernage, harmattan, climat*, "
           "orage*, humidite, weather, rain*, climate, quand partir, meilleure periode, meilleur moment, best time, "
           "when to go, canicule, secheresse",
           "meteo repere:saison"),
    _theme("fetes", "Fêtes et événements",
           "fete*, ferie*, tabaski, aid, eid, korite, magal, gamou, maouloud, mouloud, mawlid, tamkharit, achoura, ramadan, "
           "carnaval, festival*, jazz, independance, noel, paques, toussaint, assomption, ascension, pentecote, "
           "pelerinage*, popenguine, evenement*, concert*, calendrier, feast, christmas, easter",
           "fetes"),
    _theme("cuisine", "Cuisine et restaurants",
           "cuisine*, plat, manger, restaurant*, resto*, recette*, thieboudienne, thieb, yassa, mafe, domoda, ceebu jen, "
           "thiere, boisson*, bissap, bouye, cafe touba, street food, gastronomie, specialite*, petit dejeuner, dejeuner, "
           "fataya, pastel*, dibi, viande*, dessert*, vegetarien*, halal, food, dish*",
           "plats partenaires cite"),
    _theme("culture", "Culture, histoire et traditions",
           "culture*, culturel*, histoire*, historique*, tradition*, musique*, mbalax, griot*, patrimoine, musee*, theatre, "
           "danse*, tam tam, sabar, kora, cinema, litterature, ecrivain*, poete*, senghor, personnage*, esclavage, "
           "colonisation*, colonial*, royaume*, empire*, ethnie*, caste*, teranga, hospitalite, coutume*, savoir vivre",
           "histoire personnes cite"),
    _theme("langue", "Langues",
           "langue*, wolof, pulaar, pular, peul, peulh, fulfulde, serere, diola, joola, mandingue, soninke, bambara, "
           "traduire, traduction*, comment dit on, salutation*, phrase*, vocabulaire, language*, translate, speak, "
           "proverbe*, nanga def, salam aleikoum",
           "repere:langue wolof pulaar"),
    _theme("justice", "Justice et droit",
           "justice, tribunal, tribunaux, avocat*, juge*, plainte*, loi, lois, droit, droits, juridique*, legal, "
           "legalement, legalite, illegal*, legislation, decret*, succession*, divorce*, huissier*, prison*, condamn*, "
           "amende*, contravention*, proces, lawyer, corruption, constitution",
           ""),
    _theme("electricite", "Électricité et énergie",
           "electricit*, electrique*, courant electrique, coupure de courant, panne de courant, senelec, woyofal, "
           "compteur*, delestage*, solaire*, panneau solaire, groupe electrogene, onduleur*, batterie*, prise electrique, "
           "prise de courant, voltage, adaptateur*, plug, plugs, energie*, gaz, butane, carburant, essence, gasoil, "
           "electricity, power cut",
           "repere:electricite repere:factures"),
    _theme("eau", "Eau, assainissement et environnement",
           "eau potable, eau courante, eau du robinet, sen eau, seneau, sde, robinet*, forage*, puits, facture d eau, "
           "coupure d eau, assainissement, toilette*, egout*, ordures, dechet*, pollution, recyclage, plastique*, "
           "environnement, tap water",
           "repere:sante"),
    _theme("internet", "Internet, téléphone et numérique",
           "internet, wifi, sim, esim, forfait*, data, 4g, 5g, fibre, reseau mobile, telephone*, portable*, smartphone*, "
           "numero de telephone, roaming, expresso, operateur*, application*, appli, logiciel*, informatique, "
           "ordinateur*, numerique*, programmation, coder, site web, reseaux sociaux, intelligence artificielle",
           "repere:sim"),
    _theme("protection_sociale", "Protection sociale et retraite",
           "cmu, couverture maladie, assurance maladie, assurance sante, mutuelle*, retraite*, pension*, ipres, css, securite sociale, allocation*, "
           "bourse de securite familiale, bsf, cotisation*, prestations familiales, invalidite, handicap*, aide sociale",
           "repere:protection"),
    _theme("religion", "Religion",
           "religion*, religieux, islam*, musulman*, mosquee*, priere*, imam*, coran*, eglise*, chretien*, catholique*, "
           "christianisme, confrerie*, mouride*, tidjane*, tidiane, layene, khalife*, marabout*, serigne, haram, mecque, "
           "hajj, hadj, pasteur*, messe",
           "histoire personnes cite"),
    _theme("sport", "Sport et sorties",
           "sport*, football, foot, lutte, lutteur*, lions de la teranga, coupe du monde, basket*, handball, rugby, "
           "athletisme, natation, surf, kitesurf, golf, equitation, stade*, tennis, gym, fitness, boxe, marathon, "
           "jeux olympiques, coupe d afrique, loisir*, boite de nuit, discotheque, nightlife, soiree*",
           "personnes cite"),
    _theme("nature", "Nature, parcs et animaux",
           "nature, parc, parcs, reserve, reserves, reserve naturelle, faune, flore, animaux, animal, oiseau, oiseaux, "
           "mangrove*, baobab*, niokolo, djoudj, saloum, foret*, elephant*, hippopotame*, singe*, tortue*, dauphin*, "
           "baleine*, randonnee*, trek*, cascade*, chute, chutes, lac, lacs, fleuve*, riviere*, desert, dune*, "
           "ecotourisme, biodiversite, wildlife, safari*",
           "cite lieux"),
    _theme("artisanat", "Marchés, souvenirs et artisanat",
           "souvenir*, artisanat, artisan*, re:(?<!ca )marches?, marchand*, marchander, negoci*, sandaga, kermel, hlm, "
           "soumbedioune, tilene, village artisanal, tissu*, wax, bijou*, tailleur*, couturier*, boubou*, cadeau*, "
           "shopping, magasin*, centre commercial, bargain*, haggle",
           "marche cite"),
    _theme("actualite", "Actualité et politique",
           "actualite*, news, politique*, president*, gouvernement*, ministre*, ministere*, election*, assemblee nationale, "
           "depute*, maire, gouverneur, premier ministre, greve*, manifestation*, loi de finances, parlement",
           ""),
    _theme("economie", "Prix, budget et économie",
           "economie, pib, inflation, croissance, dette, demographie, population, statistique*, ansd, cout de la vie, "
           "prix, budget, combien coute, pouvoir d achat, pauvrete, developpement, investir, investissement*",
           ""),
    _theme("diaspora", "Diaspora et retour au pays",
           "diaspora*, retour au senegal, retour au pays, rentrer au pays, rentrer au senegal, retourner vivre, "
           "retourner au senegal, expatrie*, double nationalite, binational*, emigr*, immigr*, migrant*, migration, "
           "s installer au senegal, vivre au senegal",
           "repere:foncier repere:argent repere:papiers repere:protection"),
    _theme("famille", "Famille, mariage et vie sociale",
           "famille*, mariage*, marier, epouse*, epoux, mari, bapteme*, naissance*, deces, funerailles, enterrement*, "
           "ceremonie*, dot, belle famille, enfant*, bebe*, nounou, tontine*, voisin*, amitie, rencontre*, celibataire, "
           "couple*, politesse, etiquette",
           ""),
)

THEME_LABELS: dict[str, str] = {theme.id: theme.label for theme in THEMES} | {OTHER: "Autre (aucun thème reconnu)"}


def _term_regex(term: str) -> str:
    if term.startswith("re:"):
        return term[3:]
    folded = re.escape(fold_text(term.rstrip("*")))
    return folded + (r"\w*" if term.endswith("*") else r"(?:s|x)?")


def _compile(keywords: tuple[str, ...]) -> re.Pattern:
    return re.compile(r"(?<![a-z0-9])(?:" + "|".join(_term_regex(k) for k in keywords) + r")(?![a-z0-9])")


_COMPILED = tuple((theme, _compile(theme.keywords)) for theme in THEMES)

# Sujet de repères pratiques → thème : une question que seul practical_facts reconnaît (« prises ? ») garde son thème.
_PRACTICAL_THEME = {
    "urgences": "urgences", "sante": "sante", "argent": "argent", "sim": "internet", "electricite": "electricite",
    "heure": "voyage", "visa": "visa", "saison": "meteo", "entreprise": "entreprise", "transport": "transport",
    "foncier": "logement", "vente": "commerce", "papiers": "papiers", "factures": "electricite",
    "protection": "protection_sociale", "etudes": "etudes", "langue": "langue",
}

# Titres que services/senegal_knowledge.py, events.py et monetization.py mettent en début de ligne dans le contexte
# de l'IA. Si l'un d'eux change, tests/test_coverage_log.py le signale (test sur la vraie route du chat).
_MARKERS = tuple(
    (signal, re.compile("^" + marker, re.M))
    for signal, marker in (
        ("regions", "CONTEXTE RÉGIONAL PERTINENT"),
        ("lieux", "LIEUX PERTINENTS"),
        ("personnes", "PERSONNALITÉS PERTINENTES"),
        ("plats", "PLATS ET BOISSONS PERTINENTS"),
        ("histoire", "DOSSIER HISTORIQUE"),
        ("wolof", "PHRASES WOLOF SÛRES"),
        ("pulaar", "PHRASES PULAAR SÛRES"),
        ("fetes", "PROCHAINES FÊTES ET ÉVÉNEMENTS"),
        ("partenaires", "ADRESSES PARTENAIRES DE TERANGA AI"),
    )
)
_MODE_SIGNAL = {"guide": "guide", "market": "marche", "market_practice": "marche"}
# Signaux « larges » : la base choisit lieux, régions et personnages par recoupement de mots (« marche » ramène un
# marché, « religion » un lieu saint…). Ils couvrent donc peu de thèmes ; le signal « cite » (un lieu ou une région
# nommé dans la question) est plus sûr.
_LOOSE = frozenset({"lieux", "regions", "personnes"})
_REGION_NAME = re.compile(
    r"(?<![a-z0-9])(?:"
    + "|".join(sorted({re.escape(fold_text(alias)) for aliases in REGION_ALIASES.values() for alias in aliases}, key=len, reverse=True))
    + r")(?![a-z0-9])"
)

# Salutations et politesses seules : ce ne sont pas des questions, on ne les compte pas.
_SMALL_TALK = re.compile(
    r"^(?:(?:bonjour|bonsoir|salut|hello|hi|hey|coucou|salam|aleikoum|aleykum|nanga def|maa ngi fi|merci|beaucoup|thanks?|thank you|"
    r"oui|non|ok|okay|d accord|super|parfait|cool|bravo|au revoir|a bientot|bye|ca va|bien|stp|svp|s il te plait|s il vous plait|"
    r"encore|continue|suite|plus|waaw|deedeet|jerejef|jere jef|tout|et toi|et vous)(?![a-z0-9]) ?)+$"
)
_BOT_AGENT = re.compile(
    r"(?<![a-z])[a-z]*bot(?![a-z])|crawl|spider|slurp|scrap|curl|wget|python|httpx|aiohttp|go http client|java/|libwww|"
    r"headless|phantom|lighthouse|pingdom|uptime|monitor|facebookexternalhit|preview",
    re.I,
)


def looks_like_bot(user_agent: str) -> bool:
    """Robots et scripts (ou absence d'identification) : leurs « questions » ne disent rien des besoins réels."""
    agent = str(user_agent or "").strip()
    return not agent or bool(_BOT_AGENT.search(agent))


def is_small_talk(message: str) -> bool:
    """Salutation, politesse ou ponctuation seule (« Merci beaucoup ! », « ok », « ??? »)."""
    plain = " ".join(re.sub(r"[^a-z0-9]+", " ", fold_text(message)).split())
    return not plain or bool(_SMALL_TALK.match(plain))


def chat_signals(payload: dict, places=None) -> frozenset[str]:
    """Ce que le contexte de l'IA contenait pour cette question (voir _MARKERS et THEMES[*].covers)."""
    instructions = str(payload.get("instructions") or "")
    message = str(payload.get("message") or "")
    signals = {signal for signal, pattern in _MARKERS if pattern.search(instructions)}
    signals.update("repere:" + topic for topic in matching_topics(message))
    if _REGION_NAME.search(fold_text(message)) or mentioned_places(message, places):
        signals.add("cite")
    signals.update(_MODE_SIGNAL[mode] for mode in payload.get("modes") or () if mode in _MODE_SIGNAL)
    if payload.get("live_weather"):
        signals.add("meteo")
    if payload.get("use_web"):
        signals.add("web")
    return frozenset(signals)


def themes_of(message: str, signals: frozenset[str] = frozenset()) -> list[str]:
    """Thèmes de la question (identifiants du vocabulaire fermé), ou ["autre"] si aucun ne correspond."""
    folded = fold_text(message)
    found = [theme.id for theme, pattern in _COMPILED if pattern.search(folded)]
    for signal in sorted(signals):
        theme_id = _PRACTICAL_THEME.get(signal.removeprefix("repere:")) if signal.startswith("repere:") else None
        if theme_id and theme_id not in found:
            found.append(theme_id)
    if not found:
        # Un nom de lieu, de plat ou un dossier d'histoire seul (« Gorée », « yassa ») : le thème vient de ce qui est nommé.
        if "cite" in signals:
            found.append("voyage")
        elif "plats" in signals:
            found.append("cuisine")
        elif "histoire" in signals:
            found.append("culture")
    return found or [OTHER]


_BY_ID = {theme.id: theme for theme in THEMES}


def covered(theme_id: str, signals: frozenset[str]) -> bool:
    """Le contexte contenait-il quelque chose pour ce thème ? Une recherche web déclenchée suffit."""
    if "web" in signals:
        return True
    theme = _BY_ID.get(theme_id)
    # « Autre » : les signaux larges ne prouvent rien sur un sujet que personne n'a su nommer.
    return bool(signals - _LOOSE) if theme is None else bool(signals & theme.covers)


def classify(message: str, signals: frozenset[str]) -> dict[str, bool]:
    """{thème: couvert ?} pour une question."""
    return {theme_id: covered(theme_id, signals) for theme_id in themes_of(message, signals)}


def _valid_field(field: str) -> tuple[str, str] | None:
    """('total', '') ou (thème, 'c'/'n') ; None pour tout champ qui ne vient pas du vocabulaire."""
    if field == "total":
        return field, ""
    theme_id, _, state = field.partition("|")
    if state in ("c", "n") and theme_id in THEME_LABELS:
        return theme_id, state
    return None


class CoverageLog:
    def __init__(self, redis_client=None, logger=None, background: bool = True, places=None):
        self.redis = redis_client
        self.logger = logger
        self._places = places or []  # fiches de la base (noms des lieux) : seulement pour reconnaître un lieu cité
        self._background = background
        self._memory: dict[str, Counter] = {}
        self._lock = threading.Lock()
        self._writers = threading.BoundedSemaphore(8)  # écritures Redis simultanées au plus

    # --- écriture -----------------------------------------------------------------------------------------------

    def record_chat(self, payload: dict, user_agent: str = "") -> None:
        """Compte la question du chat. N'échoue jamais et n'attend jamais Redis."""
        try:
            if not isinstance(payload, dict) or payload.get("photo_only") or looks_like_bot(user_agent):
                return
            message = str(payload.get("message") or "")
            if not message.strip() or is_small_talk(message):
                return
            self.record(classify(message, chat_signals(payload, self._places)))
        except Exception as exc:  # noqa: BLE001 - le journal ne doit jamais gêner une réponse
            self._warn("coverage-log: question non comptée (%s)", type(exc).__name__)

    def record(self, states: dict[str, bool], day: _dt.date | None = None) -> None:
        """Ajoute 1 au total du jour et à chaque (thème, couvert/non couvert). Seuls les thèmes du vocabulaire sont acceptés."""
        fields = ["total"] + [
            f"{theme_id}|{'c' if is_covered else 'n'}"
            for theme_id, is_covered in states.items() if theme_id in THEME_LABELS
        ]
        if len(fields) == 1:
            return
        key = (day or _dt.date.today()).isoformat()
        if self.redis is None:
            self._store_memory(key, fields)
        elif not self._background:
            self._store_redis(key, fields)
        elif self._writers.acquire(blocking=False):
            try:
                threading.Thread(target=self._store_redis_in_background, args=(key, fields), daemon=True).start()
            except Exception:  # noqa: BLE001 - impossible de lancer le fil : comptage en mémoire
                self._writers.release()
                self._store_memory(key, fields)
        else:  # trop d'écritures Redis en attente : on ne fait pas patienter la réponse
            self._store_memory(key, fields)

    def _store_redis_in_background(self, key: str, fields: list[str]) -> None:
        try:
            self._store_redis(key, fields)
        finally:
            self._writers.release()

    def _store_redis(self, key: str, fields: list[str]) -> None:
        try:
            redis_key = _PREFIX + key
            pipe = self.redis.pipeline(transaction=False) if hasattr(self.redis, "pipeline") else None
            target = pipe if pipe is not None else self.redis
            for field in fields:
                target.hincrby(redis_key, field, 1)
            target.expire(redis_key, _KEEP_SECONDS)
            if pipe is not None:
                pipe.execute()
        except Exception as exc:  # noqa: BLE001
            self._warn("coverage-log: Redis indisponible, comptage en mémoire (%s)", type(exc).__name__)
            self._store_memory(key, fields)

    def _store_memory(self, key: str, fields: list[str]) -> None:
        limit = (_dt.date.today() - _dt.timedelta(days=KEEP_DAYS)).isoformat()
        with self._lock:
            self._memory.setdefault(key, Counter()).update(fields)
            for old in [day for day in self._memory if day < limit]:
                self._memory.pop(old, None)

    def _warn(self, message: str, *args) -> None:
        if self.logger is not None:
            self.logger.warning(message, *args)

    # --- lecture ------------------------------------------------------------------------------------------------

    def _day_counts(self, days: list[str]) -> Counter:
        counts: Counter = Counter()
        with self._lock:
            for day in days:
                counts.update(self._memory.get(day, Counter()))
        if self.redis is not None:
            try:
                keys = [_PREFIX + day for day in days]
                pipe = self.redis.pipeline(transaction=False) if hasattr(self.redis, "pipeline") else None
                if pipe is not None:
                    for key in keys:
                        pipe.hgetall(key)
                    raws = pipe.execute()
                else:
                    raws = [self.redis.hgetall(key) for key in keys]
                for raw in raws:
                    for field, value in (raw or {}).items():
                        counts[field.decode() if isinstance(field, bytes) else str(field)] += int(value)
            except Exception as exc:  # noqa: BLE001
                self._warn("coverage-log: Redis illisible (%s)", type(exc).__name__)
        return counts

    def summary(self, days: int = 30, today: _dt.date | None = None) -> dict:
        """{days, total, storage, themes: [{id, label, questions, uncovered, share}]} trié par priorité d'enrichissement :
        d'abord les thèmes qui cumulent le plus de questions sans rien dans le contexte de l'IA."""
        end = today or _dt.date.today()
        window = [(end - _dt.timedelta(days=offset)).isoformat() for offset in range(days)]
        counts = self._day_counts(window)
        per_theme: dict[str, list[int]] = {}
        for field, value in counts.items():
            parsed = _valid_field(field)
            if parsed is None or parsed[0] == "total":
                continue
            theme_id, state = parsed
            per_theme.setdefault(theme_id, [0, 0])[0 if state == "c" else 1] += value
        themes = [
            {"id": theme_id, "label": THEME_LABELS[theme_id], "questions": done + missing, "uncovered": missing,
             "share": missing / (done + missing)}
            for theme_id, (done, missing) in per_theme.items() if done + missing > 0
        ]
        themes.sort(key=lambda row: (-row["uncovered"], -row["share"], -row["questions"], row["label"]))
        return {
            "days": days,
            "total": counts.get("total", 0),
            "storage": "redis" if self.redis is not None else "memoire",
            "themes": themes,
        }
