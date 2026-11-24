"""Repères « envoi_argent » : envoyer de l'argent vers le Sénégal (ou du Sénégal vers la zone euro) et comparer.

Sources : aucun fait nouveau. La parité fixe (655,957 FCFA pour 1 €) et les services cités viennent du sujet
« argent » de services/practical_facts.py (et de services/calculators.py) ; le code secret et la vérification du
destinataire, des sujets « mobile_money » et « arnaques ». Le 19/10/2026, bceao.int (plafonds de la monnaie
électronique) et envoidargent.fr (comparateur des frais d'envoi) n'ont pas pu être ouverts depuis l'environnement
de travail : aucun frais, plafond ni délai n'est donné. Ces repères disent seulement comment comparer.
"""

# Envoyer, transférer, virer (français, anglais, wolof « yónnee »).
_ENVOI = (
    r"envoyer|envoie|envoies|envoyez|envoyons|envoient|envoyant|envoi|envois|transferer|transfere|transferes|"
    r"transferez|transfert|transferts|faire parvenir|yonnee|yonne|send|sending|sent|transfer|transfers|transferring|"
    r"wire|wiring"
)
# De l'argent : sans lui, « envoyer un colis » ou « le transfert d'un joueur » ne sont pas des envois d'argent.
_ARGENT = r"(?:\b(?:argent|euros?|fcfa|cfa|xof|francs?|sous|xaalis|money|cash|funds?)\b|€)"
# Services de transfert sans autre sens courant. « Wise » et « Ria » sont aussi des mots : il faut un autre indice.
_SERVICES = r"\b(?:western union|moneygram|remitly|worldremit|taptap send)\b"
_INDICE = r"(?:western union|moneygram|remitly|frais|moins cher|cheaper|fees?|envoi|envoyer|transfert|taux)"

TOPICS = (
    ("envoi_argent",
     rf"\b(?:{_ENVOI})\b.{{0,40}}{_ARGENT}|{_SERVICES}|\bremit\w*|\bvirements?\b|"
     rf"\b(?:wise|ria)\b.{{0,40}}\b{_INDICE}\b|\b{_INDICE}\b.{{0,40}}\b(?:wise|ria)\b",
     ("Envoyer de l'argent vers le Sénégal : services de transfert (Wave, Orange Money, Western Union, Remitly, "
      "Wise…) avec réception sur un compte mobile money ou en espèces.",
      "Comparer : le montant reçu en FCFA pour la même somme envoyée, frais compris. Frais, taux et plafonds changent "
      "selon le service et le moment : les vérifier dans l'application ou auprès du service avant chaque envoi.",
      "Euro ↔ FCFA : la parité est fixe. Pour un envoi depuis la zone euro, un taux annoncé en dessous de "
      "655,957 FCFA pour 1 € est un coût (marge ou commission de change) qui s'ajoute aux frais affichés ; dans "
      "l'autre sens (du Sénégal vers la zone euro), c'est un taux au-dessus de 655,957 FCFA pour 1 €.",
      "Avant de valider : vérifier le numéro et le nom du destinataire ; ne jamais donner son code secret, ni passer "
      "par un inconnu qui promet un meilleur taux.")),
)
SPECIFIC_FIRST = ("envoi_argent",)
