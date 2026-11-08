"""Repères « diplomes » : faire reconnaître un diplôme (reconnaissance, classement, équivalence), écoles privées.

Sources (lues le 8 novembre 2026) :
- Procédure officielle « Procédures de reconnaissance, de classement et d'équivalence des diplômes » (République du
  Sénégal, PDF publié en 2025 sur cnfplf.gouv.sn,
  https://cnfplf.gouv.sn/wp-content/uploads/2025/08/Procedures-CRCE-des-diplomes.docx.pdf) : nom de la CRCE, diplômes
  concernés (études ou formation d'au moins six mois, non pris en compte dans les statuts particuliers), usages de
  l'équivalence (corps de fonctionnaires, ordre professionnel, emploi public, concours, examen) et les cinq pièces.
- APS, 7 août 2025, « L'État ne reconnaît pas les diplômes de doctorat délivrés par les établissements
  d'enseignement supérieur privés (officiel) » : communiqué de l'ANAQ-Sup, décret n° 2021-1790 modifiant le décret
  n° 2015-582 relatif à la reconnaissance, au classement et à l'équivalence des diplômes de l'enseignement supérieur,
  vérification de l'habilitation et de l'accréditation sur le site de l'ANAQ-Sup, exception des diplômes d'État de
  docteur en médecine, pharmacie et chirurgie dentaire.
Le Journal officiel (jo.gouv.sn) n'a pas répondu ce jour-là : la date du décret de 2015 n'est pas donnée (l'APS écrit
« 1 mai », une autre source « 11 mai »). Aucune source lue ne donne le lieu de dépôt, les frais ni les délais : ils
restent « à vérifier ». L'adresse et le téléphone imprimés sur le PDF sont ceux du site qui le publie, pas forcément
ceux du guichet : ils ne sont pas repris.
"""

_DIPLOME = r"(?:diplomes?|doctorats?|licences?|masters?|bachelors?)"
_RECONNU = r"(?:equivalences?|reconnaissance|reconnaitre|reconnu|reconnus|reconnue|reconnues|homologu\w*)"

TOPICS = (
    ("diplomes",
     rf"\b{_RECONNU}\b.{{0,40}}\b{_DIPLOME}\b|\b{_DIPLOME}\b.{{0,40}}\b{_RECONNU}\b|\bcrce\b|\banaq.?sup\b",
     ("Reconnaissance d'un diplôme (par exemple obtenu à l'étranger) pour un emploi public, un concours, un examen "
      "ou un ordre professionnel : le dossier est examiné par la Commission technique de reconnaissance, de "
      "classement et d'équivalence des diplômes de l'enseignement supérieur (CRCE), selon le décret n° 2015-582 "
      "modifié par le décret n° 2021-1790. Sont concernés les diplômes obtenus après au moins six mois d'études ou "
      "de formation et non prévus par les statuts de la fonction publique.",
      "Pièces à fournir (procédure officielle publiée en 2025) : lettre au ministre chargé de la Fonction publique "
      "(« demande de reconnaissance, de classement et d'équivalence ») ; copie légalisée du diplôme ou de "
      "l'attestation de réussite ; copies légalisées du bac et des diplômes obtenus entre le bac et ce diplôme, avec "
      "les relevés de notes ; documents de l'école sur les conditions d'accès, la durée, le programme, le volume "
      "horaire ou les crédits et la délivrance du diplôme ; curriculum vitae. Lieu de dépôt, délais et frais : à "
      "vérifier auprès du ministère de la Fonction publique.",
      "École ou université privée : vérifier l'habilitation de l'établissement et l'accréditation du diplôme sur le "
      "site de l'ANAQ-Sup (Autorité nationale d'assurance qualité de l'enseignement supérieur). En août 2025, "
      "l'ANAQ-Sup a indiqué que les doctorats (PhD, doctorat unique, d'université ou d'ingénieur) délivrés par des "
      "établissements privés ne sont pas reconnus par l'État ; les diplômes d'État de docteur en médecine, en "
      "pharmacie et en chirurgie dentaire ne sont pas concernés.")),
)
SPECIFIC_FIRST = ("diplomes",)
