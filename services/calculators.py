"""Calculs fiables : c'est le code qui calcule, l'IA recopie.

Un modèle de langage qui calcule « de tête » peut se tromper de chiffres (conversion en FCFA, marge
d'un commerçant, remise, total d'un budget). Ici, une demande de calcul est détectée dans la question,
résolue avec des `Decimal`, puis injectée dans le contexte de l'IA sous la forme d'un bloc
« CALCUL VÉRIFIÉ (fait par le code, à recopier tel quel) ».

Règles de ce module :
- Les chiffres viennent uniquement de la question de l'utilisateur et de la parité fixe
  1 € = 655,957 FCFA. Aucun taux de change ni prix n'est inventé : pour le dollar, la livre ou toute autre
  devise, le taux varie, le bloc le dit et renvoie vers le convertisseur du site, sans chiffre.
- `Decimal` partout (jamais de `float` pour l'argent) ; arrondi commercial (0,5 vers le haut).
- Mieux vaut ne rien ajouter qu'un calcul douteux : écriture ambiguë (« 1,250 »), plusieurs lectures
  possibles, devises mélangées, nombre énorme ou division par zéro donnent un bloc vide ou « non calculable ».
- Rien n'est ajouté à une question sans calcul (« un hôtel à 50 000 FCFA la nuit, c'est cher ? »).
- Le texte de l'utilisateur n'est jamais recopié dans le bloc : seuls des nombres calculés et des mots
  fixes y figurent.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass, replace
from decimal import ROUND_HALF_UP, Decimal, localcontext

logger = logging.getLogger(__name__)

# Parité fixe du franc CFA (XOF) avec l'euro : 1 € = 655,957 FCFA (la même que dans practical_facts).
PARITE_FIXE = Decimal("655.957")
ENTETE = "CALCUL VÉRIFIÉ (fait par le code, à recopier tel quel) :"

_MAX_TEXTE = 2000
_MAX_VALEUR = Decimal(10) ** 15  # au-delà, ce n'est plus une somme réaliste : on ne calcule pas
_MAX_RESULTAT = Decimal(10) ** 18
_CENT = Decimal(100)
_MAX_LIGNES = 12
_MAX_POSTES = 12  # au-delà, ce n'est plus un budget qu'on additionne dans une question de chat


# ---------------------------------------------------------------------------------------------
# Fonctions pures (testables seules)
# ---------------------------------------------------------------------------------------------

def arrondir(valeur: Decimal, decimales: int = 0) -> Decimal:
    """Arrondi commercial : 0,5 vers le haut (2,5 → 3 ; 0,125 → 0,13)."""
    return valeur.quantize(Decimal(1).scaleb(-decimales), rounding=ROUND_HALF_UP)


def eur_vers_fcfa(euros: Decimal) -> Decimal:
    return euros * PARITE_FIXE


def fcfa_vers_eur(fcfa: Decimal) -> Decimal:
    return fcfa / PARITE_FIXE


def prix_de_revient(achat: Decimal, frais: tuple[Decimal, ...] | list[Decimal] = ()) -> Decimal:
    """Prix de revient = prix d'achat + frais (transport, emballage, douane…)."""
    return achat + sum(frais, Decimal(0))


def marge(vente: Decimal, revient: Decimal) -> Decimal:
    return vente - revient


def taux_de_marge(marge_: Decimal, revient: Decimal) -> Decimal | None:
    """Taux de marge (en %) = marge ÷ prix de revient. `None` si le prix de revient est nul."""
    return None if revient == 0 else marge_ / revient * _CENT


def taux_de_marque(marge_: Decimal, vente: Decimal) -> Decimal | None:
    """Taux de marque (en %) = marge ÷ prix de vente. `None` si le prix de vente est nul."""
    return None if vente == 0 else marge_ / vente * _CENT


def coefficient_multiplicateur(vente: Decimal, revient: Decimal) -> Decimal | None:
    return None if revient == 0 else vente / revient


def prix_vente_pour_taux_de_marge(revient: Decimal, taux: Decimal) -> Decimal:
    """Prix de vente qui donne ce taux de marge (en %) sur le prix de revient."""
    return revient * (1 + taux / _CENT)


def prix_vente_pour_taux_de_marque(revient: Decimal, taux: Decimal) -> Decimal | None:
    """Prix de vente qui donne ce taux de marque (en %). `None` si le taux atteint 100 % (impossible)."""
    return None if taux >= _CENT else revient / (1 - taux / _CENT)


def pourcentage_de(base: Decimal, pourcent: Decimal) -> Decimal:
    return base * pourcent / _CENT


def apres_remise(prix: Decimal, pourcent: Decimal) -> Decimal:
    return prix - pourcentage_de(prix, pourcent)


def apres_hausse(prix: Decimal, pourcent: Decimal) -> Decimal:
    return prix + pourcentage_de(prix, pourcent)


def hors_taxe(ttc: Decimal, taux: Decimal) -> Decimal:
    return ttc / (1 + taux / _CENT)


def variation_pourcent(avant: Decimal, apres: Decimal) -> Decimal | None:
    """Évolution en % de `avant` à `apres`. `None` si le point de départ est nul."""
    return None if avant == 0 else (apres - avant) / avant * _CENT


def part_pourcent(partie: Decimal, tout: Decimal) -> Decimal | None:
    return None if tout == 0 else partie / tout * _CENT


def produit(facteurs: list[Decimal] | tuple[Decimal, ...]) -> Decimal:
    resultat = Decimal(1)
    for facteur in facteurs:
        resultat *= facteur
    return resultat


def repartition(total: Decimal, parts: Decimal) -> Decimal | None:
    """Part de chacun : `None` s'il n'y a aucune part (division par zéro)."""
    return None if parts <= 0 else total / parts


# ---------------------------------------------------------------------------------------------
# Écriture des nombres (à la française)
# ---------------------------------------------------------------------------------------------

def format_nombre(valeur: Decimal, decimales: int = 0) -> str:
    """« 152500 » → « 152 500 » ; « 76.2245 » avec 2 décimales → « 76,22 »."""
    arrondi = arrondir(valeur, decimales)
    signe = "-" if arrondi < 0 else ""
    entier, _, fraction = f"{abs(arrondi):f}".partition(".")
    groupes = []
    while len(entier) > 3:
        groupes.insert(0, entier[-3:])
        entier = entier[:-3]
    groupes.insert(0, entier)
    return signe + " ".join(groupes) + ("," + fraction if decimales else "")


def _libre(valeur: Decimal) -> str:
    """Nombre sans unité : entier tel quel, sinon deux décimales."""
    centimes = arrondir(valeur, 2)
    return format_nombre(centimes, 0 if centimes == centimes.to_integral_value() else 2)


def format_pourcent(valeur: Decimal, symbole: bool = True) -> str:
    """« 33.3333 » → « 33,33 % » ; « 20.00 » → « 20 % » (sans le symbole si `symbole` est faux)."""
    texte = format_nombre(valeur, 2)
    if "," in texte:
        texte = texte.rstrip("0").rstrip(",")
    return texte + (" %" if symbole else "")


def _unite(devise: str | None, mot: str = "") -> str:
    if devise == "EUR":
        return " €"
    if devise == "XOF":
        return " FCFA"
    return " " + mot if devise == "AUTRE" and mot else ""


def format_montant(valeur: Decimal, devise: str | None = None, mot: str = "", franc: bool = False) -> str:
    """Montant avec son unité : « 152 500 FCFA », « 76,22 € ».

    Les centimes ne sont écrits que s'il y en a. Avec `franc`, un montant en FCFA à virgule ajoute son
    arrondi au franc : « 65 595,70 FCFA (65 596 FCFA au franc près) ».
    """
    centimes = arrondir(valeur, 2)
    entier = centimes == centimes.to_integral_value()
    texte = format_nombre(centimes, 0 if entier else 2) + _unite(devise, mot)
    if franc and devise == "XOF" and not entier:
        texte += f" ({format_nombre(valeur, 0)} FCFA au franc près)"
    return texte


# ---------------------------------------------------------------------------------------------
# Lecture des nombres et des montants dans la question
# ---------------------------------------------------------------------------------------------

def _borne(valeur: Decimal) -> Decimal | None:
    return valeur if 0 <= valeur <= _MAX_VALEUR else None


def parse_nombre(texte: str) -> Decimal | None:
    """Lit un nombre écrit à la française ou à l'anglaise ; `None` si l'écriture est ambiguë ou énorme.

    « 15 000 », « 15.000 », « 1 250 000 », « 15000 », « 2,5 », « 1.234,56 », « 1,234.56 » sont compris.
    « 1,250 » (virgule suivie de 3 chiffres non nuls) est ambigu (1,25 ou 1250 ?) : on ne calcule pas.
    """
    espaces = " ".join(str(texte or "").replace("'", " ").split())  # split() unifie aussi les espaces insécables
    if " " in espaces and not re.fullmatch(r"[0-9]{1,3}(?: [0-9]{3})+(?:[.,][0-9]+)?", espaces):
        return None  # « 1 00 » n'est pas un nombre bien écrit
    brut = espaces.replace(" ", "")
    if not brut or len(brut) > 40 or not re.fullmatch(r"[0-9][0-9.,]*", brut):
        return None
    if brut.isdigit():
        return _borne(Decimal(brut))
    seul = re.fullmatch(r"([0-9]{1,3})([.,])([0-9]{3})", brut)
    if seul:  # un seul séparateur suivi de 3 chiffres : milliers ou décimales ?
        entier, separateur, fraction = seul.groups()
        if entier == "0":
            return _borne(Decimal(f"0.{fraction}"))
        if separateur == "." or fraction == "000":
            return _borne(Decimal(entier + fraction))
        return None  # « 1,250 » : ambigu
    point = re.fullmatch(r"([0-9]{1,3})((?:\.[0-9]{3})+)(?:,([0-9]{1,2}))?", brut)  # 1.234.567,89
    virgule = re.fullmatch(r"([0-9]{1,3})((?:,[0-9]{3})+)(?:\.([0-9]{1,2}))?", brut)  # 1,234,567.89
    for forme, separateur in ((point, "."), (virgule, ",")):
        if forme:
            entier, milliers, decimales = forme.groups()
            return _borne(Decimal(entier + milliers.replace(separateur, "") + ("." + decimales if decimales else "")))
    simple = re.fullmatch(r"([0-9]+)[.,]([0-9]{1,2})", brut)
    if simple:
        return _borne(Decimal(f"{simple.group(1)}.{simple.group(2)}"))
    return None


_NUM = r"(?<![0-9])(?:[0-9]{1,3}(?:[ '][0-9]{3}(?![0-9]))+|[0-9]+)(?:[.,][0-9]+)*"

_DEVISE_XOF = (r"francs? cfa|f ?cfa|xof|cfa|francs?(?! (?:suisses?|belges?|francais|guineens?|congolais|cfp|rwandais|"
               r"burundais|comoriens?|djiboutiens?))|f(?![a-z0-9])")
_DEVISE_EUR = r"euros?|eur|€"
_DEVISE_AUTRE = (r"dollars?(?: (?:us|americains?|canadiens?|australiens?))?|usd|\$|cad|livres? sterling|gbp|£|pounds?|"
                 r"dirhams?|mad|yuans?|rmb|yens?|jpy|nairas?|ngn|cedis?|ghs|rands?|zar|roupies?|inr|riyals?|dinars?|"
                 r"shekels?|pesos?|reais|brl|chf|francs? (?:suisses?|belges?|guineens?|congolais|cfp|rwandais|burundais|"
                 r"comoriens?|djiboutiens?)|livres?(?= (?:en|in|to|into|vers) (?:fcfa|cfa|francs? cfa|xof|euros?|eur|€))")
_DEVISE = rf"(?P<dev>(?P<d_xof>{_DEVISE_XOF})|(?P<d_eur>{_DEVISE_EUR})|(?P<d_autre>{_DEVISE_AUTRE}))(?![a-z])"
_DEVISE_SANS_NOM = rf"(?:{_DEVISE_XOF}|{_DEVISE_EUR}|{_DEVISE_AUTRE})(?![a-z])"
_MULT = r"k|mille|millions?|milliards?"

_MONTANT = re.compile(
    rf"(?:(?<![a-z])(?P<pre>€|\$|£|eur|usd|xof|fcfa|cfa)\s?)?"
    rf"(?P<n>{_NUM})"
    rf"(?:\s?(?P<mult>{_MULT})(?![a-z]))?"
    rf"(?:\s?(?:de |d )?{_DEVISE})?"
)
_PRE_DEVISE = {"€": "EUR", "eur": "EUR", "$": "AUTRE", "usd": "AUTRE", "£": "AUTRE", "xof": "XOF", "fcfa": "XOF", "cfa": "XOF"}
_POURCENT_SUIT = re.compile(r"\s?(?:%|pour ?cents?|percent)")
# Ce qui peut suivre un prix écrit sans monnaie. Un mot qui n'est pas dans cette liste (« 3 sacs », « 50 pièces »)
# signale une quantité, pas un montant.
_SUIVI_MONTANT_NU = re.compile(
    r"\s*(?:$|[,.;:!?)\]+=/-]|(?:a|et|ou|puis|pour|de|d|sur|par|le|la|l|les|un|une|chez|au|aux|contre|soit|alors|donc|"
    r"mais|avec|sans|ttc|ht|piece|unite|chacun|chacune|kg|kilo|litre|environ|net|brut|cash|liquide|en)(?![a-z]))"
)
_MOIS = re.compile(
    r"\s?(?:janvier|fevrier|mars|avril|mai|juin|juillet|aout|septembre|octobre|novembre|decembre|january|february|"
    r"march|april|june|july|august|september|october|november|december)(?![a-z])"
)
_LIEN_INTERVALLE = re.compile(r"\s?(?:-|a|et|ou|or|to|/|jusqu a|jusqu au)\s?")


@dataclass(frozen=True)
class Montant:
    valeur: Decimal | None  # None : écriture ambiguë, nombre négatif ou trop grand
    devise: str | None  # "EUR", "XOF", "AUTRE" ou None
    mot: str  # devise telle qu'écrite (pour les devises « autres »)
    debut: int
    fin: int
    nu: bool  # ni monnaie ni « k » / « mille » / « million »
    quantite: bool  # nombre nu suivi d'un mot (« 3 sacs ») : c'est une quantité, pas un montant
    date: bool = False  # année (« 2026 ») ou jour suivi d'un mois (« 15 octobre ») : ni prix, ni quantité à compter

    @property
    def compte(self) -> bool:
        """Nombre qui compte quelque chose (« 3 sacs », « 50 pièces ») sans être une date."""
        return self.quantite and not self.date


def _facteur_multiplicateur(mot: str) -> Decimal:
    if mot in ("k", "mille"):
        return Decimal(1000)
    return Decimal(10) ** (9 if mot.startswith("milliard") else 6)


def _devise_du_groupe(m: re.Match) -> tuple[str | None, str]:
    pre = m.groupdict().get("pre")  # absent de l'expression qui cherche la devise cible
    if pre:
        return _PRE_DEVISE[pre], pre
    if m.group("d_xof") is not None:
        return "XOF", m.group("dev")
    if m.group("d_eur") is not None:
        return "EUR", m.group("dev")
    if m.group("d_autre") is not None:
        return "AUTRE", m.group("dev")
    return None, ""


def _montants(texte: str) -> list[Montant]:
    resultat: list[Montant] = []
    for m in _MONTANT.finditer(texte):
        debut_n = m.start("n")
        if not m.group("pre") and debut_n > 0 and texte[debut_n - 1].isalpha():
            continue  # « H2O », « x3 » : le nombre fait partie d'un mot
        if _POURCENT_SUIT.match(texte, m.end()):
            continue  # « 20 % » est un pourcentage, pas un montant
        devise, mot = _devise_du_groupe(m)
        avant = texte[m.start() - 1:m.start()]
        apres = texte[m.end():m.end() + 1]
        if devise is None and (avant in ("/", ":") or apres in ("/", ":")):
            continue  # date ou heure (12/05/2026, 10:30)
        valeur = parse_nombre(m.group("n"))
        if valeur is not None and m.group("mult"):
            valeur = _borne(valeur * _facteur_multiplicateur(m.group("mult")))
        if avant == "-" and (m.start() < 2 or texte[m.start() - 2] in " ("):
            valeur = None  # montant négatif : on ne devine pas
        nu = devise is None and not m.group("mult")
        quantite = date = False
        if nu:
            quantite = not _SUIVI_MONTANT_NU.match(texte, m.end())
            annee = valeur is not None and re.fullmatch(r"[0-9]{4}", m.group("n")) and 1900 <= valeur <= 2100
            date = bool(annee or (quantite and _MOIS.match(texte, m.end())))
            quantite = quantite or bool(annee)  # une année n'est pas un prix
        resultat.append(Montant(valeur, devise, mot, m.start(), m.end(), nu, quantite, date))
    # « 50-100 euros », « 3000 à 4500 FCFA » : le premier nombre prend la devise du second.
    for i in range(len(resultat) - 1):
        courant, suivant = resultat[i], resultat[i + 1]
        if (courant.nu and suivant.devise and _LIEN_INTERVALLE.fullmatch(texte[courant.fin:suivant.debut])
                and courant.valeur is not None):
            resultat[i] = replace(courant, devise=suivant.devise, mot=suivant.mot, nu=False, quantite=False)
    return resultat


@dataclass(frozen=True)
class Pourcent:
    valeur: Decimal | None
    signe: str
    debut: int
    fin: int


_POURCENT = re.compile(
    r"(?P<signe>(?<![0-9a-z])[-+]\s?)?(?P<n>[0-9]+(?:[.,][0-9]+)?)\s?(?:%|pour ?cents?|percent)"
)


def _pourcentages(texte: str) -> list[Pourcent]:
    resultat = []
    for m in _POURCENT.finditer(texte):
        valeur = parse_nombre(m.group("n"))
        if valeur is not None and valeur > 10_000:
            valeur = None
        resultat.append(Pourcent(valeur, (m.group("signe") or "").strip(), m.start(), m.end()))
    return resultat


# ---------------------------------------------------------------------------------------------
# Unités (jours, personnes…) et quantités
# ---------------------------------------------------------------------------------------------

_UNITES = (
    ("jour", r"jours?|journees?|days?"),
    ("nuit", r"nuits?|nuitees?|nights?"),
    ("semaine", r"semaines?|weeks?"),
    ("mois", r"mois|months?"),
    ("personne", r"personnes?|pers|adultes?|enfants?|voyageurs?|touristes?|persons?|people|adults?|children|kids?|"
                 r"travell?ers?|tetes?|heads?"),
    ("chambre", r"chambres?|rooms?"),
    ("repas", r"repas|meals?"),
    ("trajet", r"trajets?|courses?|trips?|rides?"),
    ("billet", r"billets?|tickets?"),
)
_NOMS_UNITES = {
    "jour": ("jour", "jours"), "nuit": ("nuit", "nuits"), "semaine": ("semaine", "semaines"), "mois": ("mois", "mois"),
    "personne": ("personne", "personnes"), "chambre": ("chambre", "chambres"), "repas": ("repas", "repas"),
    "trajet": ("trajet", "trajets"), "billet": ("billet", "billets"),
}
_CLASSES = tuple((nom, re.compile(motif)) for nom, motif in _UNITES)
_UNITE_ANY = "|".join(f"(?:{motif})" for _, motif in _UNITES)
_TEMPS = r"jours?|nuits?|nuitees?|semaines?|mois|days?|nights?|weeks?|months?"
_MOTS_NOMBRES = {
    "deux": 2, "trois": 3, "quatre": 4, "cinq": 5, "six": 6, "sept": 7, "huit": 8, "neuf": 9,
    "dix": 10, "onze": 11, "douze": 12, "treize": 13, "quatorze": 14, "quinze": 15, "seize": 16, "vingt": 20,
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
}
_MOTS_RE = "|".join(sorted(_MOTS_NOMBRES, key=len, reverse=True))
_QUANTITE = re.compile(
    rf"(?<![0-9a-z.,])(?:(?P<n>{_NUM})\s?|(?P<w>{_MOTS_RE})\s)(?P<u>{_UNITE_ANY})(?![a-z])"
)
_PAR_UNITE = (rf"(?P<u1>{_UNITE_ANY})(?![a-z])"
              rf"(?:\s?(?:et|and|,|/|&)\s?(?:par |per |/)?\s?(?P<u2>{_UNITE_ANY})(?![a-z]))?")
_MARQUEUR = re.compile(rf"\s?(?:par|per|/|la|le|l|chaque|each)\s?{_PAR_UNITE}")


def _classe(mot: str) -> str | None:
    for nom, motif in _CLASSES:
        if motif.fullmatch(mot):
            return nom
    return None


def _classes(m: re.Match) -> list[str]:
    """Unités citées par « par personne et par nuit » (sans doublon, dans l'ordre)."""
    noms = [_classe(m.group("u1"))] + ([_classe(m.group("u2"))] if m.group("u2") else [])
    return list(dict.fromkeys(nom for nom in noms if nom))


@dataclass(frozen=True)
class Quantite:
    classe: str
    n: Decimal
    debut: int
    fin: int


def _quantites(texte: str) -> list[Quantite]:
    resultat = []
    for m in _QUANTITE.finditer(texte):
        classe = _classe(m.group("u"))
        n = parse_nombre(m.group("n")) if m.group("n") is not None else Decimal(_MOTS_NOMBRES[m.group("w")])
        if classe is not None and n is not None:
            resultat.append(Quantite(classe, n, m.start(), m.end()))
    return resultat


def _libelle_quantite(classe: str, n: Decimal) -> str:
    if not classe:  # nombre d'objets d'un nom inconnu (« 3 moutons »)
        return _libre(n)
    singulier, pluriel = _NOMS_UNITES[classe]
    return f"{format_nombre(n)} {singulier if n == 1 else pluriel}"


def _quantite_unique(classe: str, quantites: list[Quantite]) -> Quantite | None:
    """La quantité de cette classe, si elle n'est donnée qu'une fois (« 2 adultes et 2 enfants » : on ne devine pas)."""
    trouvees = [q for q in quantites if q.classe == classe]
    return trouvees[0] if len(trouvees) == 1 else None


# ---------------------------------------------------------------------------------------------
# Signaux dans la question
# ---------------------------------------------------------------------------------------------

_CIBLE = re.compile(
    rf"(?:\ben\b|\bin\b|\binto\b|\bto\b|\bvers\b|\bsoit\b|->|=>|→|=|combien (?:de |d )?|how many |how much in )"
    rf"\s?\??\s?(?:des |de |d |les |la |le |l )?{_DEVISE}"
)
# Demande de conversion sans devise cible écrite. « Ça fait combien ? » seul n'en est pas une (c'est souvent un total).
_CUE_CONVERSION = re.compile(
    r"convert\w*|\bchange(?:r|z|s)?\b|taux (?:de change|d echange|du jour|actuel)|equival\w*|"
    r"(?:vaut|valent|vaudrait) combien|worth|exchange|"
    r"(?:combien (?:vaut|valent|font|fait)|how much (?:is|are)) (?:donc |alors |about )?(?=[0-9€$£])"
)
# L'utilisateur impose son propre taux : la parité fixe n'est pas celle qu'il demande.
_TAUX_IMPOSE = re.compile(
    r"taux\s?(?:de|d|a|:|=)?\s?[0-9]|rate\s?(?:of|:|=|is)?\s?[0-9]|au cours (?:de |du jour )?[0-9]|"
    r"a [0-9][0-9 .,]* (?:fcfa|cfa|francs?(?: cfa)?) (?:pour|le|l) ?(?:1 )?(?:euro|eur|€)"
)
_CUE_TOTAL = re.compile(
    r"\btotal\b|\btotale?s?\b|au total|en tout|combien (?:ca|cela) (?:fait|coute|va couter|revient|donne)|"
    r"combien (?:font|faut il|me faut|dois je|coute|couteront|coutent|va couter)|how much (?:in total|total|will|would|do i)|in total|altogether|"
    r"ca fait combien|ca coute combien|ca revient a combien|ca donne combien|additionn\w*|cumul\w*|"
    r"la somme de|fais la somme|somme totale|sum of|add up|adds up"
)
_CUE_TOTAL_STRICT = re.compile(
    r"\btotal\b|\btotale?s?\b|au total|en tout|additionn\w*|cumul\w*|la somme de|fais la somme|somme totale|"
    r"in total|altogether|sum of|add up|adds up"
)
_CUE_ADDITION = re.compile(r"[0-9a-z€$£] ?\+ ?[0-9€$£]")  # « 100 € + 50 € »
_ALTERNATIVE = re.compile(r"\bou\b|\bor\b|\bentre\b|\bbetween\b")
_CUE_RESTE = re.compile(r"\breste\w*|\brestant\w*|\bleft\b|\bremaining\b|\bdepasse\w*|\bsuffi\w*|\benough\b")
_CUE_BUDGET = re.compile(
    r"budget|j ai|dispose\w*|enveloppe|i have|my budget|nous avons|on a\b|economis\w*|epargn\w*|salaire|gagne\w*|"
    r"revenu|income|earn\w*|apport|capital|cagnotte"
)


def _cible(texte: str) -> tuple[str, str] | None:
    m = _CIBLE.search(texte)
    if not m:
        return None
    devise, mot = _devise_du_groupe(m)
    return (devise, mot) if devise else None


# ---------------------------------------------------------------------------------------------
# (a) Conversion euro ↔ FCFA
# ---------------------------------------------------------------------------------------------

@dataclass(frozen=True)
class Total:
    valeur: Decimal
    devise: str | None
    mot: str


def _note_taux_variable(mots: list[str]) -> str:
    noms = " / ".join(dict.fromkeys(mots))
    return (
        f"- Conversion avec « {noms} » : le taux de change varie chaque jour, donc aucun chiffre n'est calculé ici "
        "(ne pas inventer de taux). Renvoyer vers le convertisseur de la page d'accueil de teranga-ai.fr (euro, "
        "dollar US, livre sterling) ou vers le taux du jour d'une banque ou d'un bureau de change."
    )


def _ligne_eur_vers_fcfa(euros: Decimal) -> str:
    fcfa = eur_vers_fcfa(euros)
    if fcfa > _MAX_RESULTAT:
        return ""
    return f"- {format_montant(euros, 'EUR')} = {format_montant(fcfa, 'XOF', franc=True)}, parité fixe : 1 € = 655,957 FCFA."


def _ligne_fcfa_vers_eur(fcfa: Decimal) -> str:
    euros = fcfa_vers_eur(fcfa)
    texte = "moins de 0,01 €" if 0 < euros < Decimal("0.005") else format_montant(euros, "EUR")
    return f"- {format_montant(fcfa, 'XOF')} = {texte} (arrondi au centime), parité fixe : 1 € = 655,957 FCFA."


def _lignes_conversion(sources: list[tuple[Decimal, str, str]], cible: tuple[str, str] | None) -> list[str]:
    lignes: list[str] = []
    autres: list[str] = []
    for valeur, devise, mot in sources:
        destination = cible[0] if cible else {"EUR": "XOF", "XOF": "EUR"}.get(devise, "AUTRE")
        if devise == destination and (devise != "AUTRE" or (cible and mot.rstrip("s") == cible[1].rstrip("s"))):
            continue  # « 100 euros en euros » : rien à convertir
        if {devise, destination} == {"EUR", "XOF"}:
            ligne = _ligne_eur_vers_fcfa(valeur) if devise == "EUR" else _ligne_fcfa_vers_eur(valeur)
            if ligne:
                lignes.append(ligne)
        else:
            if devise == "AUTRE":
                autres.append(mot)
            if cible and destination == "AUTRE":
                autres.append(cible[1])
    if autres:
        lignes.append(_note_taux_variable(autres))
    return list(dict.fromkeys(lignes))


def _conversion(texte: str, montants: list[Montant], cible: tuple[str, str] | None, total: Total | None,
                autres_lignes: bool) -> list[str]:
    if _TAUX_IMPOSE.search(texte):
        return []
    if total is not None:
        # Le total d'un budget, converti seulement si la question le demande clairement.
        if cible is None or total.devise not in ("EUR", "XOF"):
            return []
        return _lignes_conversion([(total.valeur, total.devise, total.mot)], cible)
    if autres_lignes or not (cible is not None or _CUE_CONVERSION.search(texte)):
        return []
    sources = [(m.valeur, m.devise, m.mot) for m in montants if m.devise and m.valeur is not None and not m.quantite]
    return _lignes_conversion(list(dict.fromkeys(sources))[:3], cible)


# ---------------------------------------------------------------------------------------------
# (b) Commerçant : prix de revient, marge, taux de marge, taux de marque
# ---------------------------------------------------------------------------------------------

_ROLES = (
    ("cout", re.compile(r"achet\w*|achat\w*|paye\w*|payer|cout\w*|revient|acquis\w*|bought|buy\w*|purchas\w*|cost\w*|"
                        r"fournisseur|grossiste|prix de gros")),
    ("vente", re.compile(r"vend\w*|vente\w*|sell\w*|\bsold\b|prix client|prix public|prix de detail|je le mets|"
                         r"je le propose|je le fais|prix affiche")),
    ("frais", re.compile(r"frais|transport|emballage|livraison|douane|manutention|stockage|carburant|essence|fret|"
                         r"expedition|main d oeuvre")),
    ("marge", re.compile(r"marge|benefice|gain\b|profit|margin")),
)
_CUE_MARCHAND = re.compile(
    r"marge|benefice|profit|\bgain\b|gagn\w*|perte|perd\w*|rentab\w*|revient|markup|margin|coefficient|marque"
)
_MARQUE = re.compile(r"marque")
_SUR_COUT = re.compile(r"taux de marge|sur (?:le |mon )?(?:prix d achat|cout|prix de revient)|au dessus")
_MARGE_PCT = re.compile(r"marge|benefice|gain\b|profit|margin|markup|marque|gagner")
_UNITE_PRIX = re.compile(r"\s?(?:par|le|la|les|l|/|per)\s?([a-z0-9]+)")
_UNITES_NEUTRES = frozenset({"piece", "pieces", "unite", "article", "articles", "chacun", "chacune", "un", "une"})


# Mot qui suit le montant : « 1 500 de marge », « 300 de transport ».
_ROLES_APRES = (
    ("marge", re.compile(r"\s?(?:de |d |en )?(?:marge|benefice|gain|profit)")),
    ("frais", re.compile(r"\s?(?:de |d )?(?:frais|transport|emballage|livraison|douane|manutention|stockage|carburant|"
                         r"fret|expedition)")),
    ("cout", re.compile(r"\s?(?:de |d )?(?:prix d achat|achat|cout|prix de revient)")),
    ("vente", re.compile(r"\s?(?:de |d )?(?:prix de vente|vente)")),
)


def _role(texte: str, montant: Montant, borne: int) -> str | None:
    """Rôle d'un montant : le dernier mot-clé qui le précède (« j'achète à… », « je vends… »), sinon celui qui le suit."""
    fenetre = texte[max(borne, montant.debut - 45):montant.debut]
    meilleur: tuple[int, str] | None = None
    for nom, motif in _ROLES:
        for m in motif.finditer(fenetre):
            if meilleur is None or m.end() > meilleur[0]:
                meilleur = (m.end(), nom)
    if meilleur:
        return meilleur[1]
    return next((nom for nom, motif in _ROLES_APRES if motif.match(texte, montant.fin)), None)


def _marchand(texte: str, montants: list[Montant], pourcents: list[Pourcent], quantites: list[Quantite]) -> list[str]:
    if not _CUE_MARCHAND.search(texte):
        return []
    roles: dict[str, list[Montant]] = {"cout": [], "vente": [], "frais": [], "marge": []}
    borne = 0
    for m in montants:
        if m.quantite:
            continue  # « j'achète 50 sacs à 3000 » : la quantité ne coupe pas la phrase
        role = _role(texte, m, borne)
        borne = m.fin
        if role:
            if m.valeur is None:
                return []
            roles[role].append(m)
        elif _est_prix(m):
            return []  # un prix dont on ignore le rôle (« à 3000, à 3500 et je vends… ») : on ne devine pas
    if len(roles["cout"]) > 1 or len(roles["vente"]) > 1 or len(roles["marge"]) > 1:
        return []
    retenus = [m for liste in roles.values() for m in liste]
    cles = {(m.devise, m.mot.rstrip("s") if m.devise == "AUTRE" else "") for m in retenus if m.devise}
    if not retenus or len(cles) > 1:
        return []  # rien d'exploitable, ou devises mélangées : on ne convertit pas
    devise = next(iter(cles))[0] if cles else None
    mot = next((m.mot for m in retenus if m.devise), "")
    # Achat et vente doivent porter sur la même base : « 2 sacs à 3 000 » et « 5 000 les 2 » ne se comparent pas.
    unites = [u.group(1) for u in (_UNITE_PRIX.match(texte, m.fin) for m in roles["cout"] + roles["vente"]) if u]
    deux_bases = sum(bool(roles[r]) for r in ("cout", "vente", "marge")) >= 2
    avec_quantites = bool(quantites) or any(m.compte for m in montants)
    if any(u.isdigit() for u in unites) or len(set(unites)) > 1:
        return []
    if deux_bases and avec_quantites and not (roles["cout"] and roles["vente"] and len(unites) == 2):
        return []  # des quantités sont citées : seuls deux prix « au même sac » sont comparables
    if len(unites) == 1 and unites[0] not in _UNITES_NEUTRES:
        return []  # un seul des deux prix est « par sac » ou « au kilo »

    def argent(valeur: Decimal, franc: bool = False) -> str:
        return format_montant(valeur, devise, mot, franc)

    cout = roles["cout"][0].valeur if roles["cout"] else None
    vente = roles["vente"][0].valeur if roles["vente"] else None
    marge_donnee = roles["marge"][0].valeur if roles["marge"] else None
    frais = [m.valeur for m in roles["frais"]]
    revient = prix_de_revient(cout, frais) if cout is not None else None
    if vente is None and revient is not None and marge_donnee is not None:
        vente = revient + marge_donnee
    elif revient is None and vente is not None and marge_donnee is not None and not frais:
        revient = cout = vente - marge_donnee
    if revient is None:
        return []
    lignes: list[str] = []
    if frais:
        detail = " + ".join([_libre(cout)] + [_libre(f) for f in frais])
        lignes.append(f"- Prix de revient (achat + frais) : {detail} = {argent(revient)}.")
    if vente is None:
        pct = _pourcent_de_marge(texte, pourcents)
        if pct is not None:
            return _lignes_prix_de_vente(revient, pct, argent)
        return lignes if frais and "revient" in texte else []
    if abs(revient) > _MAX_RESULTAT or abs(vente) > _MAX_RESULTAT:
        return []
    ecart = marge(vente, revient)
    if not frais:
        lignes.append(f"- Prix de revient (prix d'achat) : {argent(revient)}.")
    calcul = f"{_libre(vente)} - {_libre(revient)} = {argent(ecart)}"
    if ecart > 0:
        lignes.append(f"- Marge : {calcul} (prix de vente - prix de revient).")
    elif ecart < 0:
        lignes.append(f"- Perte : {calcul} (le prix de vente est inférieur au prix de revient).")
    else:
        lignes.append(f"- Marge nulle : prix de vente = prix de revient = {argent(vente)}.")
    tm = taux_de_marge(ecart, revient)
    lignes.append("- Taux de marge (marge ÷ prix de revient) : "
                  + (format_pourcent(tm) if tm is not None else "non calculable (prix de revient nul)") + ".")
    tq = taux_de_marque(ecart, vente)
    lignes.append("- Taux de marque (marge ÷ prix de vente) : "
                  + (format_pourcent(tq) if tq is not None else "non calculable (prix de vente nul)") + ".")
    coef = coefficient_multiplicateur(vente, revient)
    if coef is not None:
        lignes.append(f"- Coefficient multiplicateur (prix de vente ÷ prix de revient) : {format_nombre(coef, 2)}.")
    return lignes


def _pourcent_de_marge(texte: str, pourcents: list[Pourcent]) -> tuple[Decimal, str] | None:
    """Taux voulu par le commerçant : (valeur, "marge" | "marque" | "les deux"), ou None."""
    if len(pourcents) != 1 or pourcents[0].valeur is None:
        return None
    p = pourcents[0]
    fenetre = texte[max(0, p.debut - 30):p.fin + 30]
    if not _MARGE_PCT.search(fenetre):
        return None
    if _MARQUE.search(fenetre):
        return p.valeur, "marque"
    return p.valeur, "marge" if _SUR_COUT.search(fenetre) else "les deux"


def _lignes_prix_de_vente(revient: Decimal, pct: tuple[Decimal, str], argent) -> list[str]:
    taux, genre = pct
    t = format_pourcent(taux)
    lignes = [f"- Prix de revient : {argent(revient)}."]
    if genre in ("marge", "les deux"):
        prix = prix_vente_pour_taux_de_marge(revient, taux)
        if prix > _MAX_RESULTAT:
            return []
        lignes.append(f"- Taux de marge de {t} (marge ÷ prix de revient) : prix de vente = {_libre(revient)} x "
                      f"(1 + {format_pourcent(taux, False)} ÷ 100) = {argent(prix, True)}, soit une marge de "
                      f"{argent(prix - revient)}.")
    if genre in ("marque", "les deux"):
        prix = prix_vente_pour_taux_de_marque(revient, taux)
        if prix is None:
            lignes.append(f"- Taux de marque de {t} : impossible, la marge ne peut pas atteindre 100 % du prix de vente.")
        elif prix > _MAX_RESULTAT:
            return []
        else:
            lignes.append(f"- Taux de marque de {t} (marge ÷ prix de vente) : prix de vente = {_libre(revient)} ÷ "
                          f"(1 - {format_pourcent(taux, False)} ÷ 100) = {argent(prix, True)}, soit une marge de "
                          f"{argent(prix - revient)}.")
    if genre == "les deux":
        lignes.append("- La question ne dit pas s'il s'agit d'un taux de marge ou d'un taux de marque : présenter les "
                      "deux, ou demander lequel.")
    return lignes


# ---------------------------------------------------------------------------------------------
# (c) Pourcentages et remises
# ---------------------------------------------------------------------------------------------

_CUE_REMISE = re.compile(
    r"remise|reduction|rabais|\bsoldes?\b|promo\w*|ristourne|discount|baisse|diminu\w*|deconte|escompte|reduc\w*|"
    r"(?<!au )(?<!ou )moins|\boff\b|\bsale\b|bradage|decote"
)
_CUE_HAUSSE = re.compile(
    r"augment\w*|hausse|majorat\w*|supplement|surcout|surcharge|increase|markup|plus cher|revaloris\w*"
)
_CUE_TAXE = re.compile(r"\btva\b|taxes?\b|\btax\b|\bvat\b|frais|commission|pourboire|\btip\b|interets?")
_CUE_TTC = re.compile(r"\bttc\b")
_QUESTION_POURCENT = re.compile(r"pourcentage|pour ?cents?|percent|en %|\bpct\b")
_LIEN_EVOLUTION = re.compile(r"(?:et )?(?:passe |monte |descend |augmente |baisse )?(?:a|to|vers|->|→|jusqu a)")
_LIEN_AU_LIEU = re.compile(r"au lieu de|instead of|contre")
_LIEN_PART = re.compile(
    r"sur|out of|on|/|represente(?:nt)?(?: quel(?:le)? (?:pourcentage|part))?(?: de| du)?|"
    r"est quel pourcentage de|is what percent of"
)


def _base_du_pourcentage(texte: str, p: Pourcent, candidats: list[Montant]) -> Montant | None:
    """Le montant sur lequel porte le pourcentage : le plus proche après lui, ou le seul de la question."""
    apres = [m for m in candidats if m.debut >= p.fin and len(texte[p.fin:m.debut]) <= 40
             and not re.search(r"[0-9]", texte[p.fin:m.debut])]
    if apres:
        return apres[0]
    return candidats[0] if len(candidats) == 1 else None


def _pourcents(texte: str, montants: list[Montant], pourcents: list[Pourcent],
               quantites: list[Quantite]) -> tuple[list[str], Total | None]:
    """Lignes de calcul, et le montant final (prix après remise ou hausse) qu'on peut convertir ensuite."""
    candidats = [m for m in montants if not m.quantite]
    if pourcents and (quantites or any(m.compte for m in montants)):
        return [], None  # « 20 % sur 5 nuits à 40 000 » : la base de la remise n'est pas claire
    if any(_MARGE_PCT.search(texte[max(0, p.debut - 30):p.fin + 30]) for p in pourcents):
        return [], None  # « 30 % de marge » : taux de marge ou de marque, pas un simple pourcentage
    if len(pourcents) == 1:
        return _pourcent_simple(texte, pourcents[0], candidats)
    if not pourcents and _QUESTION_POURCENT.search(texte):
        return _pourcent_demande(texte, candidats), None
    return [], None


def _pourcent_simple(texte: str, p: Pourcent, candidats: list[Montant]) -> tuple[list[str], Total | None]:
    if p.valeur is None or any(m.valeur is None for m in candidats):
        return [], None
    base = _base_du_pourcentage(texte, p, candidats)
    if base is None or base.valeur is None:
        return [], None
    remise = bool(p.signe == "-" or _CUE_REMISE.search(texte))
    hausse = bool(p.signe == "+" or _CUE_HAUSSE.search(texte))
    taxe = bool(_CUE_TAXE.search(texte))
    ttc = bool(_CUE_TTC.search(texte))
    explicite = bool(re.match(r"\s?(?:de |d |du |sur |of |on |off )", texte[p.fin:p.fin + 8])
                     or re.search(r"(?:de |d |du |sur |of |on )$", texte[max(0, p.debut - 8):p.debut]))
    if not (remise or hausse or taxe or ttc or explicite) or (remise and (hausse or taxe)):
        return [], None
    v, pct = base.valeur, p.valeur
    if v * pct > _MAX_RESULTAT * _CENT:
        return [], None

    def argent(valeur: Decimal) -> str:
        return format_montant(valeur, base.devise, base.mot)

    part = pourcentage_de(v, pct)
    t = format_pourcent(pct)
    if ttc and (taxe or hausse):
        ht = hors_taxe(v, pct)
        return [f"- {argent(v)} TTC avec {t} de taxe : prix hors taxe = {_libre(v)} ÷ (1 + {format_pourcent(pct, False)} ÷ 100) = {argent(ht)} ; "
                f"taxe = {_libre(v)} - {_libre(ht)} = {argent(v - ht)}."], None
    if remise:
        if pct > _CENT:
            return [], None
        final = apres_remise(v, pct)
        return [f"- Remise de {t} sur {argent(v)} : {_libre(v)} x {format_pourcent(pct, False)} ÷ 100 = {argent(part)} de réduction ; "
                f"prix après remise : {_libre(v)} - {_libre(part)} = {argent(final)}."], Total(final, base.devise, base.mot)
    if hausse:
        final = apres_hausse(v, pct)
        return [f"- Hausse de {t} sur {argent(v)} : {_libre(v)} x {format_pourcent(pct, False)} ÷ 100 = {argent(part)} ; nouveau montant : "
                f"{_libre(v)} + {_libre(part)} = {argent(final)}."], Total(final, base.devise, base.mot)
    ligne = f"- {t} de {argent(v)} = {argent(part)}"
    if taxe:  # TVA, frais, commission : ajoutés au montant ou retirés de lui, la question ne le dit pas
        ligne += f" ; si ce montant s'ajoute : {argent(apres_hausse(v, pct))}"
        if pct <= _CENT:
            ligne += f" ; s'il se retire : {argent(apres_remise(v, pct))}"
    return [ligne + "."], None


def _pourcent_demande(texte: str, candidats: list[Montant]) -> list[str]:
    """« De 10 000 à 12 500, quelle évolution en % ? », « 3 000 sur 15 000 en pourcentage »."""
    if len(candidats) != 2 or any(m.valeur is None for m in candidats):
        return []
    a, b = candidats
    lien = texte[a.fin:b.debut].strip()
    if _LIEN_AU_LIEU.fullmatch(lien):  # « 12 000 au lieu de 15 000 »
        a, b = b, a
        lien = "a"
    if _LIEN_EVOLUTION.fullmatch(lien):
        taux = variation_pourcent(a.valeur, b.valeur)
        if taux is None:
            return [f"- Évolution de {_libre(a.valeur)} à {_libre(b.valeur)} : non calculable (point de départ nul)."]
        sens = "hausse" if taux > 0 else "baisse" if taux < 0 else "aucun changement"
        return [f"- Évolution de {format_montant(a.valeur, a.devise, a.mot)} à {format_montant(b.valeur, b.devise, b.mot)} : "
                f"({_libre(b.valeur)} - {_libre(a.valeur)}) ÷ {_libre(a.valeur)} x 100 = "
                f"{'+' if taux > 0 else ''}{format_pourcent(taux)} ({sens})."]
    if _LIEN_PART.fullmatch(lien):
        taux = part_pourcent(a.valeur, b.valeur)
        if taux is None:
            return [f"- {_libre(a.valeur)} sur {_libre(b.valeur)} : non calculable (division par zéro)."]
        return [f"- {format_montant(a.valeur, a.devise, a.mot)} sur {format_montant(b.valeur, b.devise, b.mot)} : "
                f"{_libre(a.valeur)} ÷ {_libre(b.valeur)} x 100 = {format_pourcent(taux)}."]
    return []


# ---------------------------------------------------------------------------------------------
# (d) Budget : quantité x prix, somme de postes, reste, répartition
# ---------------------------------------------------------------------------------------------

_FACTEUR = (rf"(?:{_NUM})(?:\s?(?:{_MULT})(?![a-z]))?(?:\s?(?:de |d )?{_DEVISE_SANS_NOM})?"
            rf"(?:\s?(?:{_UNITE_ANY})(?![a-z]))?")
_CHAINE = re.compile(rf"(?<![0-9a-z]){_FACTEUR}(?:\s?(?:x|\*|fois)\s?{_FACTEUR})+")
# « 5 nuits à » juste avant un prix : le prix est par nuit si la question demande un total.
_TEMPS_A = re.compile(
    rf"(?<![0-9a-z.,])(?:(?P<n>{_NUM})\s?|(?P<w>{_MOTS_RE})\s)(?P<u>{_TEMPS})(?![a-z])\s?(?:a|at|@)\s?"
)
_CHACUN = re.compile(r"\s?(?:chacun|chacune|each|l un|l une|l unite|la piece|piece|par tete)(?![a-z])")
_ENTRE_QUANTITE_ET_PRIX = re.compile(r"[^0-9.;?!]{0,25}")
_QUESTION_PAR = (
    re.compile(rf"(?:combien|how much|quel(?:le)? (?:budget|montant|somme)|what).{{0,40}}?(?:par|per|/|chaque|each)\s?"
               rf"{_PAR_UNITE}"),
    re.compile(rf"(?:par|per|chaque|each)\s?{_PAR_UNITE}.{{0,25}}?(?:combien|how much)"),
)


@dataclass(frozen=True)
class Terme:
    """Un poste du budget : ligne de calcul (produits), valeur, devise, position et quantités utilisées."""
    texte: str
    valeur: Decimal
    devise: str | None
    mot: str
    debut: int
    fin: int
    produit: bool
    utilise: tuple[int, ...] = ()  # positions des quantités (« 5 nuits ») consommées par ce produit


def _devise_commune(termes: list[Terme]) -> tuple[bool, str | None, str]:
    cles = {(t.devise, t.mot.rstrip("s") if t.devise == "AUTRE" else "") for t in termes if t.devise}
    if len(cles) > 1:
        return False, None, ""
    if not cles:
        return True, None, ""
    return True, next(iter(cles))[0], next(t.mot for t in termes if t.devise)


def _est_prix(m: Montant) -> bool:
    """Montant utilisable comme prix : jamais une quantité ; un nombre nu doit valoir au moins 100."""
    return m.valeur is not None and not m.quantite and (m.devise is not None or not m.nu or m.valeur >= 100)


def _un_produit(m: Montant, facteurs: list[tuple[str, Decimal]], debut: int, fin: int,
                utilise: tuple[int, ...]) -> Terme | None:
    valeur = produit([m.valeur] + [n for _, n in facteurs])
    if valeur > _MAX_RESULTAT:
        return None
    detail = " x ".join([_libelle_quantite(c, n) for c, n in facteurs] + [_libre(m.valeur)])
    return Terme(f"- {detail} = {format_montant(valeur, m.devise, m.mot)}.", valeur, m.devise, m.mot,
                 debut, fin, True, utilise)


def _produits_par_unite(texte: str, montants: list[Montant], quantites: list[Quantite]) -> list[Terme | None]:
    """« 40 000 FCFA par nuit » + « 5 nuits » ; « 30 000 par personne et par jour » ; « 4 personnes à 25 000 chacune ».

    None signale un prix dont la quantité manque ou reste ambiguë : aucun total fiable.
    """
    resultat: list[Terme | None] = []
    for m in montants:
        if not _est_prix(m):
            continue
        marqueur = _MARQUEUR.match(texte, m.fin)
        if marqueur:
            trouves = [_quantite_unique(c, quantites) for c in _classes(marqueur)]
            if not trouves or None in trouves:
                resultat.append(None)
                continue
            facteurs = [(q.classe, q.n) for q in trouves]
            resultat.append(_un_produit(m, facteurs, m.debut, marqueur.end(), tuple(q.debut for q in trouves)))
            continue
        chacun = _CHACUN.match(texte, m.fin)
        if chacun:  # « 3 moutons à 150 000 l'un » : le prix est celui d'un seul objet
            avant = [q for q in quantites if q.fin <= m.debut and _ENTRE_QUANTITE_ET_PRIX.fullmatch(texte[q.fin:m.debut])]
            proche = max(avant, key=lambda q: q.fin) if avant else None
            resultat.append(_un_produit(m, [(proche.classe, proche.n)], m.debut, chacun.end(), (proche.debut,))
                            if proche else None)
    return resultat


def _produits_a_la_nuit(texte: str, montants: list[Montant]) -> list[Terme | None]:
    """« 5 nuits à 40 000 FCFA » quand la question demande un total : le prix est par nuit."""
    fins = {m.end(): m for m in _TEMPS_A.finditer(texte)}
    resultat: list[Terme | None] = []
    for m in montants:
        if not _est_prix(m) or _MARQUEUR.match(texte, m.fin) or _CHACUN.match(texte, m.fin):
            continue
        avant = fins.get(m.debut)
        if avant is None:
            continue
        n = parse_nombre(avant.group("n")) if avant.group("n") is not None else Decimal(_MOTS_NOMBRES[avant.group("w")])
        classe = _classe(avant.group("u"))
        resultat.append(_un_produit(m, [(classe, n)], avant.start(), m.fin, (avant.start(),))
                        if n is not None and classe else None)
    return resultat


def _produits_explicites(texte: str, total_demande: bool) -> list[Terme | None]:
    """Multiplications écrites : « 3 x 15 000 FCFA », « 2 x 5 x 30k », « 3 fois 25 000 »."""
    resultat: list[Terme | None] = []
    for chaine in _CHAINE.finditer(texte):
        facteurs = [f for f in _MONTANT.finditer(chaine.group(0)) if not _POURCENT_SUIT.match(chaine.group(0), f.end())]
        valeurs = [parse_nombre(f.group("n")) for f in facteurs]
        if len(facteurs) < 2 or None in valeurs:
            resultat.append(None)
            continue
        devises = {_devise_du_groupe(f) for f in facteurs} - {(None, "")}
        monetaire = any(f.group("pre") or f.group("dev") or f.group("mult") for f in facteurs)
        if len(devises) > 1 or (not monetaire and not total_demande):
            continue
        valeurs = [v * (_facteur_multiplicateur(f.group("mult")) if f.group("mult") else 1)
                   for f, v in zip(facteurs, valeurs)]
        valeur = produit(valeurs)
        if valeur > _MAX_RESULTAT or any(v > _MAX_VALEUR for v in valeurs):
            resultat.append(None)
            continue
        devise, mot = next(iter(devises)) if devises else (None, "")
        resultat.append(Terme(f"- {' x '.join(_libre(v) for v in valeurs)} = {format_montant(valeur, devise, mot)}.",
                              valeur, devise, mot, chaine.start(), chaine.end(), True))
    return resultat


def _comptages(montants: list[Montant], quantites: list[Quantite]) -> list[Quantite]:
    """Tout ce que la question compte : « 5 nuits » (unité connue) et « 3 moutons » (nom inconnu, classe vide)."""
    nus = [Quantite("", m.valeur, m.debut, m.fin) for m in montants
           if m.compte and m.valeur is not None and not any(q.debut <= m.debut < q.fin for q in quantites)]
    return sorted(quantites + nus, key=lambda q: q.debut)


def _produits_incertains(comptes: list[Quantite], produits: list[Terme | None]) -> bool:
    """Vrai si un total serait peut-être faux : prix sans quantité, produits qui se recouvrent, quantité oubliée."""
    if None in produits:
        return True
    termes = [t for t in produits if t is not None]
    zones = sorted((t.debut, t.fin) for t in termes)
    if any(suivant[0] < courant[1] for courant, suivant in zip(zones, zones[1:])):
        return True  # « 2 x 35 000 la nuit pour 4 nuits » : deux lectures du même prix
    if termes:  # « 2 chambres… 4 nuits » : une quantité qui n'entre dans aucun calcul fausserait le total
        return any(not any(q.debut in t.utilise or t.debut <= q.debut < t.fin for t in termes) for q in comptes)
    # Sans produit : si la question compte quelque chose (« pour 3 personnes », « 7 jours »), un prix est peut-être
    # unitaire et une simple addition serait fausse.
    return bool(comptes)


def _budget(texte: str, montants: list[Montant], quantites: list[Quantite]) -> tuple[list[str], Total | None]:
    division = _repartition(texte, montants, quantites)
    if division:
        return division, None
    total_demande = bool(_CUE_TOTAL.search(texte))
    comptes = _comptages(montants, quantites)
    produits = _produits_par_unite(texte, montants, comptes)
    if total_demande:
        produits += _produits_a_la_nuit(texte, montants)
    produits += _produits_explicites(texte, total_demande)
    if _produits_incertains(comptes, produits):
        return [], None
    termes = sorted((t for t in produits if t is not None), key=lambda t: t.debut)
    devises = {(m.devise, m.mot.rstrip("s") if m.devise == "AUTRE" else "") for m in montants
               if m.devise and m.valeur is not None and not m.quantite}
    devise_texte = next(iter(devises))[0] if len(devises) == 1 else None
    mot_texte = next((m.mot for m in montants if m.devise), "")
    # Postes simples. Un nombre nu n'en est un que si le texte ne mélange pas plusieurs monnaies.
    simples = [Terme(_libre(m.valeur), m.valeur, m.devise or devise_texte, m.mot or mot_texte, m.debut, m.fin, False)
               for m in montants
               if _est_prix(m) and not any(t.debut <= m.debut < t.fin for t in termes)
               and (m.devise or len(devises) <= 1)]
    tous = sorted(termes + simples, key=lambda t: t.debut)
    if len(tous) > _MAX_POSTES:
        return [], None
    reste = _lignes_reste(texte, tous, simples, total_demande)
    if reste is not None:
        return reste, None
    plusieurs_postes = len(tous) >= 2
    somme_demandee = bool(_CUE_TOTAL_STRICT.search(texte) or _CUE_ADDITION.search(texte)) or (total_demande and bool(termes))
    if not termes and not (plusieurs_postes and somme_demandee and not _ALTERNATIVE.search(texte)):
        return [], None
    ok, devise, mot = _devise_commune(tous)
    lignes = [t.texte for t in termes]
    if not ok:
        return lignes, None
    if plusieurs_postes and somme_demandee:
        somme = sum((t.valeur for t in tous), Decimal(0))
        if somme > _MAX_RESULTAT:
            return lignes, None
        detail = " + ".join(_libre(t.valeur) for t in tous)
        lignes.append(f"- Total : {detail} = {format_montant(somme, devise, mot)}.")
        return lignes, Total(somme, devise, mot)
    if len(tous) == 1:
        return lignes, Total(termes[0].valeur, devise, mot)
    return lignes, None


def _lignes_reste(texte: str, tous: list[Terme], simples: list[Terme], total_demande: bool) -> list[str] | None:
    """« J'ai 500 000 FCFA, hôtel 150 000, vol 200 000 : combien me reste-t-il ? » ; None si ce n'est pas le cas."""
    if not simples or not (_CUE_RESTE.search(texte) or total_demande):
        return None
    enveloppe = simples[0]
    if not _CUE_BUDGET.search(texte[max(0, enveloppe.debut - 45):enveloppe.debut]):
        return None
    depenses = [t for t in tous if t is not enveloppe]
    ok, devise, mot = _devise_commune(tous)
    if not depenses or not ok or any(t.debut < enveloppe.debut for t in depenses):
        return None
    somme = sum((t.valeur for t in depenses), Decimal(0))
    lignes = [t.texte for t in depenses if t.produit]
    if len(depenses) > 1:
        lignes.append(f"- Total des dépenses : {' + '.join(_libre(t.valeur) for t in depenses)} = "
                      f"{format_montant(somme, devise, mot)}.")
    reste = enveloppe.valeur - somme
    calcul = f"{_libre(enveloppe.valeur)} - {_libre(somme)} = {format_montant(reste, devise, mot)}"
    if reste >= 0:
        lignes.append(f"- Reste : {calcul}.")
    else:
        lignes.append(f"- Budget dépassé : {calcul} (il manque {format_montant(-reste, devise, mot)}).")
    return lignes


def _repartition(texte: str, montants: list[Montant], quantites: list[Quantite]) -> list[str]:
    """« 500 000 FCFA pour 10 jours, combien par jour ? » → 50 000 FCFA par jour."""
    question = next((m for m in (p.search(texte) for p in _QUESTION_PAR) if m), None)
    if question is None:
        return []
    classes = _classes(question)
    sommes = [m for m in montants if _est_prix(m) and not _MARQUEUR.match(texte, m.fin)]
    if len(sommes) != 1 or not classes:
        return []
    somme = sommes[0]
    trouves = [_quantite_unique(c, quantites) for c in classes]
    if None in trouves:
        return []
    nombres = [q.n for q in trouves]
    diviseur = " x ".join(_libelle_quantite(c, n) for c, n in zip(classes, nombres))
    part = repartition(somme.valeur, produit(nombres))
    debut = f"- {format_montant(somme.valeur, somme.devise, somme.mot)} ÷ {diviseur}"
    if part is None:
        return [debut + " : non calculable (division par zéro)."]
    noms = " et par ".join(_NOMS_UNITES[c][0] for c in classes)
    return [f"{debut} = {format_montant(part, somme.devise, somme.mot)} par {noms}."]


# ---------------------------------------------------------------------------------------------
# Point d'entrée
# ---------------------------------------------------------------------------------------------

_ESPACES_SPECIAUX = re.compile("[\u00a0\u2007\u2009\u202f]")  # espaces insécables et fines
_INVISIBLES = re.compile("[\u200b-\u200d\u2060\ufeff]")  # caractères de largeur nulle
_CHIFFRE = re.compile(r"[0-9]")
_NOMBRE_DEMESURE = re.compile(r"[0-9][0-9.,]{40,}")  # 40 chiffres d'affilée : ce n'est pas une somme


def _preparer(question: object) -> str:
    """Minuscules sans accents ; apostrophes et traits d'union entre lettres changés en espaces."""
    brut = unicodedata.normalize("NFD", str(question or "")[:_MAX_TEXTE].casefold())
    texte = "".join(c for c in brut if not unicodedata.combining(c))
    texte = _INVISIBLES.sub("", _ESPACES_SPECIAUX.sub(" ", texte))
    texte = (texte.replace("’", "'").replace("‘", "'").replace("`", "'").replace("−", "-")
             .replace("×", " x ").replace("✕", " x "))
    texte = re.sub(r"(?<=[a-z])['-](?=[a-z])", " ", texte)
    return re.sub(r"\s+", " ", texte)


def _calculs(question: object) -> list[str]:
    with localcontext() as contexte:
        contexte.prec = 50
        texte = _preparer(question)
        if not _CHIFFRE.search(texte) or _NOMBRE_DEMESURE.search(texte):
            return []
        montants = _montants(texte)
        pourcents = _pourcentages(texte)
        quantites = _quantites(texte)
        cible = _cible(texte)
        lignes = _marchand(texte, montants, pourcents, quantites)
        if lignes:
            return lignes[:_MAX_LIGNES]
        lignes, total = _pourcents(texte, montants, pourcents, quantites)
        if lignes:
            return (lignes + _conversion(texte, montants, cible, total, True))[:_MAX_LIGNES]
        lignes, total = _budget(texte, montants, quantites)
        return (lignes + _conversion(texte, montants, cible, total, bool(lignes)))[:_MAX_LIGNES]


def calculation_block(question: object) -> str:
    """Bloc « CALCUL VÉRIFIÉ » pour la question, ou "" si elle ne demande aucun calcul."""
    try:
        lignes = _calculs(question)
    except Exception as erreur:  # un calcul raté ne doit jamais faire échouer le chat
        logger.warning("calculators_failed %s", type(erreur).__name__)
        return ""
    return ENTETE + "\n" + "\n".join(lignes) if lignes else ""
