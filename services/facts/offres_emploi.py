"""Repère « offres_emploi » : à qui cherche un emploi ou un stage, proposer la page /offres-emploi de Teranga AI.

Source : la page /offres-emploi de ce site (services/offres_emploi.py, 22 novembre 2026). Elle renvoie vers la page
d'offres de sites vérifiés à la main ce jour-là (Emploi Dakar, Senjob, Concoursn) et vers le guichet unique de l'ANPEJ
(emploijeunes.sn) ; elle ne recopie aucune offre. Teranga ne lit pas ces offres : l'IA ne peut donc ni en citer une,
ni dire si elle est encore ouverte.

Déclencheurs : « emploi » seul sert aussi à « emploi du temps » et « mode d'emploi », « travail » seul à « travaux »,
« droit du travail » ou « travail à domicile » : seuls comptent « offre(s) d'emploi / de stage », chercher ou trouver
un emploi, un travail, un job, un boulot ou un stage, la recherche d'emploi, les sites d'emploi, et l'anglais « job
offers », « find a job », « job search », « looking for a job ».
"""

TOPICS = (
    ("offres_emploi",
     r"\boffres? d ?emplois?\b|\boffres? de (stages?|travail|jobs?)\b|"
     r"\b(cherch|trouv|recherch)\w* (du |un |une |mon |un premier )?(emploi|travail|job|boulot|stage)\b|"
     r"\brecherche d ?emploi\b|\bsites? d ?(emploi|offres)\b|"
     r"\bjob offers?\b|\bjob search\b|\b(find|finding|looking for|get|search for) (a )?(job|internship)\b",
     ("Page « Offres d'emploi au Sénégal » de Teranga AI : https://teranga-ai.fr/offres-emploi. Elle renvoie vers "
      "des sites d'offres vérifiés le 22 novembre 2026 (Emploi Dakar, Senjob, Concoursn) et vers le guichet unique de "
      "l'ANPEJ (emploijeunes.sn), le service public d'inscription des jeunes demandeurs d'emploi. On postule "
      "directement sur ces sites ; Teranga n'affiche pas les offres lui-même.",
      "Quand la personne cherche un emploi ou un stage : lui proposer ce lien et l'outil gratuit « Mon CV » "
      "(https://teranga-ai.fr/cv). Ne jamais citer une offre, un employeur ou une date limite qui n'est pas dans la "
      "question ; rappeler qu'une vraie offre ne demande jamais d'argent.")),
)
SPECIFIC_FIRST = ("offres_emploi",)
