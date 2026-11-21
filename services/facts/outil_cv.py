"""Repère « outil_cv » : proposer l'outil gratuit « Mon CV » de Teranga AI à qui parle de CV ou de lettre de motivation.

Source : la page /cv de ce site (services/cv.py et static/cv.js, 21 novembre 2026). Elle accepte un ancien CV (PDF,
Word ou photo, 2 Mo au plus) ou le récit du parcours, le poste visé et, au choix, le texte d'une offre ; elle rend un
CV en 9 modèles à enregistrer en PDF, et une lettre de motivation quand une offre est collée. La consigne de l'IA
interdit d'ajouter diplôme, expérience ou compétence. Ce n'est pas un fait extérieur qui change : pas de vérification
en direct (services/web_policy.py).

Déclencheurs : « cv » seul est aussi la puissance d'une voiture (« 7 CV », « 110 cv », « CV fiscaux ») ; un nombre juste
avant ou « fiscaux » juste après l'écartent. « résumé » (anglais « resume ») veut dire autre chose en français : écarté.
"""

TOPICS = (
    ("outil_cv",
     r"\bcurriculum\b|\blettres? de motivation\b|\bcover letters?\b|(?<!\d)(?<!\d )\bcvs?\b(?! fiscaux)",
     ("Outil gratuit « Mon CV » de Teranga AI (page en français) : https://teranga-ai.fr/cv. On y envoie son ancien "
      "CV (PDF, Word ou photo, 2 Mo au plus) ou on raconte son parcours, on indique le poste visé et, si on veut, le "
      "texte d'une offre d'emploi. Teranga crée un CV clair, au choix parmi 9 modèles, à enregistrer en PDF, et une "
      "lettre de motivation quand une offre est collée. Il n'invente ni diplôme, ni expérience, ni compétence.",
      "Quand la personne veut faire, refaire ou adapter son CV ou sa lettre de motivation : l'aider dans la réponse, "
      "puis lui proposer ce lien pour obtenir le document mis en page.")),
)
SPECIFIC_FIRST = ("outil_cv",)
