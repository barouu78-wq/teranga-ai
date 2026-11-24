"""Repères sur le droit du travail au Sénégal : généraux, prudents, sans chiffre non sourcé.

Sources (consultées le 10 octobre 2026 par recherche web ; les pages elles-mêmes n'ont PAS pu être ouvertes depuis
l'environnement de travail, le réseau sortant refusant tous les sites visés : les textes ont été relus dans les
extraits renvoyés par le moteur de recherche, d'où les formulations « selon la presse » et « à vérifier ») :
- Nouveau Code du travail (loi n° 2026-18 du 3 septembre 2026, qui remplace la loi n° 97-17 du 1er décembre 1997) :
  adoption par l'Assemblée nationale le 18 août 2026 (rts.sn, koaci.com, allafrica.com), promulgation le 3 septembre,
  publication au Journal officiel n° 7931 du 17 septembre 2026 et entrée en vigueur le 18 septembre (vie-publique.sn,
  dakar92.com, pulse.sn « officiellement en vigueur », 30/09/2026, allafrica.com du 30/09/2026) ; plus de cinquante
  textes d'application annoncés en préparation (allafrica.com, 01/10/2026). Nouveautés rapportées : télétravail encadré,
  congé de maternité de 14 à 18 semaines, chapitre sur le harcèlement et les discriminations, fin de la conciliation
  préalable obligatoire, CDD écrit (seneplus.com, vie-publique.sn, pulse.sn, dakar92.com).
- Ancien Code (loi n° 97-17 du 1er décembre 1997) : fiche NATLEX de l'OIT (natlex.ilo.org, notice 49603), uniquement
  pour savoir ce qui a été remplacé : AUCUN article, durée ni montant de l'ancien code n'est repris ici.
- Durée maximale du CDD et nombre de renouvellements : les articles de presse se contredisent (deux ans avec un seul
  renouvellement, ou quatre ans avec plusieurs renouvellements, selon qu'ils décrivent le projet ou le texte promulgué).
  Aucun chiffre n'est donc donné.
- Salaire minimum (SMIG / SMAG) : fixé par décret (décret n° 2018-1048 du 11 juin 2018, décret n° 2023-1710 cités par des
  sites de ressources humaines) ; les montants relevés sur ces sites se contredisent, aucun n'est repris.
Congés payés, préavis, indemnités, période d'essai, durée du travail : non confirmés dans le texte de 2026 (source
manquante : le texte de la loi n° 2026-18 au Journal officiel) ; le sujet les renvoie à l'inspection du travail.
"""

TOPICS = (
    ("travail",
     r"\bcode du travail\b|\bdroit du travail\b|\bdroits? (du |des )?(travailleurs?|salaries?|employes?)\b|"
     r"\bcontrats? de travail\b|\bcontrats? a duree (determinee|indeterminee)\b|\bcdd\b|\bcdi\b|"
     r"\blicenci\w+|\bconges? (payes?|annuels?|de maternite|de paternite|de maladie)\b|\bconges? maternite\b|"
     r"\bsmig\b|\bsmag\b|\bsalaires? minimum\b|\bsalaire minimal\b|"
     r"\b(inspection|inspecteur|tribunal|juge) du travail\b|\bconvention collective\b|"
     r"\bbulletins? (de |du )?(paie|salaire)\b|\bfiches? de paie\b|"
     r"\bperiode d essai\b|\bpreavis (de |d )?(licenciement|demission|depart)\b|\blettres? de (licenciement|demission)\b|"
     r"\bindemnites? de (licenciement|depart|fin de contrat)\b|\bheures supplementaires\b|"
     r"\bharcelement (moral|sexuel|au travail|professionnel)\b|\bteletravail\b|"
     r"\bsalaires? (impaye|non paye|en retard)s?\b|\b(arrieres|retards?) de salaires?\b|"
     r"\brupture (abusive )?(de |du )?(mon |son |le )?contrat\b|"
     r"\bmon (employeur|patron)\b.{0,50}\b(paie|paye|payer|renvoie|renvoyer|licencie|contrat|salaire|conges?)\b|"
     r"\blabou?r (law|code)\b|\bemployment (law|contract)\b|\bminimum wage\b|\b(wrongful|unfair) dismissal\b|"
     r"\bmaternity leave\b",
     ("Nouveau Code du travail : le Sénégal a adopté un nouveau Code du travail, la loi n° 2026-18 du 3 septembre 2026 "
      "(votée par l'Assemblée nationale le 18 août 2026, publiée au Journal officiel du 17 septembre 2026 et présentée "
      "par la presse comme en vigueur depuis le 18 septembre 2026). Il remplace la loi n° 97-17 du 1er décembre 1997. "
      "Plus de cinquante textes d'application (décrets, arrêtés) étaient annoncés en préparation début octobre 2026. "
      "Les articles, durées et montants cités par des guides, vidéos ou sites antérieurs à septembre 2026 (congés, "
      "préavis, indemnités, période d'essai, durée du travail…) peuvent donc avoir changé : ne pas les citer de "
      "mémoire, les présenter comme « à vérifier » et renvoyer vers l'inspection du travail ou le texte publié au "
      "Journal officiel.",
      "Nouveautés rapportées par la presse (à vérifier dans le texte publié) : un cadre pour le télétravail, qui "
      "n'existait pas dans le code de 1997 ; un congé de maternité porté de 14 à 18 semaines ; un chapitre sur la "
      "violence et le harcèlement et une lutte renforcée contre les discriminations ; la fin de la conciliation "
      "préalable obligatoire avant d'aller devant le juge du travail ; un contrat à durée déterminée (CDD) qui doit "
      "être écrit. Pour la durée maximale d'un CDD et le nombre de renouvellements, les articles de presse ne "
      "s'accordent pas : ne donner aucun chiffre sans avoir lu le texte officiel.",
      "Salaire minimum : le SMIG (salaire minimum interprofessionnel garanti) et le SMAG (agricole) sont fixés par "
      "décret et révisés de temps à autre. Les montants affichés sur internet se contredisent (certains sites "
      "reprennent des chiffres de 2018 ou de 2023) : ne pas en donner de mémoire, et renvoyer vers le ministère "
      "chargé du Travail ou le Journal officiel pour le montant en vigueur.",
      "Litige avec un employeur (salaire non payé, licenciement contesté, harcèlement) : garder le contrat, les bulletins "
      "de paie, la lettre de licenciement éventuelle et les messages échangés ; s'adresser à l'inspection du travail de "
      "sa région ou à un syndicat, puis, si besoin, au juge du travail (tribunal du travail) ; un avocat peut conseiller "
      "sur le texte applicable. Aucune issue n'est garantie. Un cas précis (ancienneté, motif, convention collective) "
      "se juge sur le texte en vigueur, pas sur une règle générale.")),
)

SPECIFIC_FIRST = ("travail",)
