# Audit V3 — 02. Benchmark de l'écosystème de l'IA au Sénégal

Date de la recherche : 25 octobre 2026. Préparé pour le propriétaire de Teranga AI (https://teranga-ai.fr).
Code de Teranga consulté : `main` au commit `c8e999d`.

## Résumé

1. En 2026, l'IA en langues nationales s'est accélérée au Sénégal : modèles vocaux ouverts **Kiriku** (AI Hub Sénégal, publiés vers août 2026), famille **Oolel** (Soynade Research : texte, voix, recherche) et API commerciales (Soynade, Andakia **AWA**).
2. Pour Teranga, trois acteurs seulement offrent une brique technique intégrable (Kiriku, Soynade, Andakia). Les sept autres sont des services d'un secteur précis (emploi, éducation, santé, route, agriculture) ou des sources de données (Vie Publique Sénégal, corpus Kallaama de Jokalante).
3. Aucune qualité vocale n'est démontrée de façon indépendante. Les taux d'erreur publiés viennent des auteurs et ne concordent pas d'une source à l'autre. Exemple : pour M-Kiriku-ASR, la fiche annonce 16,34 % d'erreurs de mots en wolof, et plus de 40 % en pulaar et en sérère.
4. Le réseau de la session ne laissait passer que GitHub. Hugging Face et tous les sites officiels étaient illisibles, si bien qu'une grande partie des informations est classée « Déclaré (extrait) » et reste à relire.
5. Recommandation : monter un **banc vocal hors production** qui compare le système actuel (`gpt-4o-transcribe` et `gpt-4o-mini-tts`) à Kiriku, Soynade, Omnilingual ASR et ElevenLabs. Avant tout usage commercial, faire vérifier chaque licence par écrit.

## Légende des statuts

| Statut | Sens dans ce document |
|---|---|
| **Vérifié** | Lu directement pendant cette session sur une source primaire : dépôt GitHub du projet, fichier de licence, code, README officiel. Pour un chiffre publié par un auteur, « Vérifié » signifie seulement « l'auteur publie bien ce chiffre », pas « le chiffre est juste ». |
| **Déclaré** | Affirmation du projet ou de la presse, non vérifiable ici. **« Déclaré (extrait) »** : la page primaire (souvent une fiche Hugging Face) existe mais n'a pas pu être ouverte ; le fait vient d'un extrait de moteur de recherche, qui peut comporter des erreurs. |
| **Hypothèse** | Déduction de l'audit, à confirmer. |
| **Non disponible** | Rien trouvé. |

## Tableau comparatif

| Acteur | Offre (ce qui est documenté) | Langues | Ouvert / licence | Intégrable par Teranga ? | Statut des infos |
|---|---|---|---|---|---|
| **AI Hub Sénégal — Kiriku** | Modèles de reconnaissance vocale (M-Kiriku-ASR, Kiriku-Wolof-ASR) et de synthèse vocale (Kiriku-Wolof-TTS, Kiriku-Pulaar-TTS) sur Hugging Face ; Kiriku Voice Challenge | wolof, pulaar, sérère (reconnaissance) ; wolof, pulaar (synthèse) | Poids publiés (Déclaré) ; licence **non lue** (Non disponible) | Oui techniquement : un projet lauréat les utilise (Vérifié). Licence à clarifier, et impossible à héberger sur l'offre Render actuelle | Mixte |
| **Soynade Research — Oolel** | LLM wolof Oolel-v0.1 (7,6 à 8 milliards de paramètres), Oolel-Small, Oolel-Corrector, synthèse Oolel-Voices, reconnaissance Wolof-HuBERT-CTC, recherche Oolel-Embed ; API payante et Studio | wolof (plus le mélange wolof-français en synthèse) | Code GitHub AGPL-3.0 (Vérifié) ; Oolel-v0.1 apache-2.0 et Oolel-Voices agpl-3.0 (Déclaré, extrait) | Oui par l'API (tarifs non lus) ou par les poids (revue juridique AGPL nécessaire) | Mixte |
| **Andakia — AWA** | API AWA (transcription, synthèse, analyse, indexation) ; assistant web, mobile, WhatsApp, téléphone | wolof ; pulaar annoncé en 2026 | Propriétaire ; kit Python Apache-2.0 (Vérifié, copie miroir) | Oui par l'API commerciale (tarif sur devis) | Surtout Déclaré |
| **Institut des Algorithmes du Sénégal (IAS)** | Formations en IA (plateforme KOCC), PAS Challenge 2026, diagnostic de maturité IA | français (Hypothèse) | Non disponible | Pas de techno à intégrer ; partenariat de formation possible | Déclaré |
| **Jokalante — NAFOORE** | Conseil agricole et climatique (radio, SMS, voix, WhatsApp), robot conversationnel vocal à IA générative ; porteur du corpus vocal Kallaama | wolof, sérère, pulaar, diola, mandingue, français, anglais (Déclaré) | Service propriétaire ; corpus Kallaama en CC-BY-4.0 (Vérifié) | Corpus réutilisable pour un banc (avec attribution) ; une « API voix et NLP » figure au catalogue (Déclaré) | Mixte |
| **Sunu SOUBA** | Mise en relation emploi par apprentissage automatique ; Sunu Souba Lab | Non disponible | Non disponible | Faible (renvoi éventuel) | Déclaré |
| **Jangalma** | Révisions de la 6e à la terminale, assistant IA « COOC » (écrit « Kocc » dans la presse), cours à domicile | français (Hypothèse) | Propriétaire, sur abonnement | Faible | Déclaré |
| **KadduCare** | Seul fait trouvé : nommé aux prix SMSI 2026, catégorie e-santé | Non disponible | Non disponible | Non disponible | Non disponible |
| **AI-Karangué** | Télématique IA pour flottes : caméras de bord avec aide à la conduite et détection de fatigue, traceurs GPS, plateforme Karangué221 | sans objet | Propriétaire ; matériel de tiers (Déclaré) | Non (hors du champ de Teranga) | Déclaré |
| **Vie Publique Sénégal** | Plus de 10 000 documents publics avec recherche plein texte, application ; page d'assistant conversationnel dans le code ; coorganisateur du Kiriku Voice Challenge | français | Code GPL-3.0 (Vérifié) | Par partenariat de données ou par liens ; pas d'API publique documentée ; code GPL non réutilisable dans un code fermé | Mixte |

---

## 1. AI Hub Sénégal et les modèles vocaux Kiriku

Contexte : le projet Sen Hub IA a été conçu par le ministère de la Communication, des Télécommunications et du
Numérique, le GIE AI Hub Sénégal et l'ambassade de France ([ai-hubsenegal.sn, extrait](https://ai-hubsenegal.sn/en/portfolios/senhubia/)).
Statut : Déclaré.

| Point | Constat | Statut | Source |
|---|---|---|---|
| 1. Fonctionnalités disponibles | Quatre dépôts Hugging Face au nom d'`AIHubSN` : `M-Kiriku-ASR` (reconnaissance multilingue), `Kiriku-Wolof-ASR`, `Kiriku-Wolof-TTS`, `Kiriku-Pulaar-TTS`. Les quatre identifiants sont chargés par le code d'un lauréat du challenge (`backend/kiriku_models.py`). Ils existent donc et sont téléchargeables, au moins avec un jeton Hugging Face. | Vérifié (par le code d'un tiers) | [github.com/MaDi-12/tewlu-kaddu](https://github.com/MaDi-12/tewlu-kaddu) |
| | Recensement des chercheurs : les quatre modèles sont datés d'août 2026. | Vérifié (source secondaire) | [State-of-NLP-Research-in-Senegal](https://github.com/DerXter/State-of-NLP-Research-in-Senegal) |
| | Kiriku Voice Challenge : 74 candidatures, 15 équipes, 10 finalistes, plus de 2 millions de FCFA de prix, accompagnement d'un à deux mois ; résultats annoncés à Dakar le 16 octobre 2026 ; organisation AI Hub Sénégal et Vie Publique Sénégal, avec l'ambassade de France. | Déclaré | [APS](https://aps.sn/intelligence-artificielle-15-equipes-selectionnees-pour-developper-des-solutions-vocales-en-langues-nationales/), [allAfrica](https://fr.allafrica.com/stories/202610160715.html), [RTS](https://www.rts.sn/actualite/detail/a-la-une/ia-et-langues-nationales-le-kiriku-voice-challenge-valorise-linnovation-numerique-au-senegal) |
| | Lauréats : TekTalma, 1er prix (informations de transport à la voix) ; Tewlu Kaddu, 2e (ventes, crédits et stock des petits commerçants par notes vocales WhatsApp) ; Sunuchat, 3e (santé sur WhatsApp, réponses fondées sur des sources officielles). | Déclaré | [RTS](https://www.rts.sn/actualite/detail/a-la-une/ia-et-langues-nationales-le-kiriku-voice-challenge-valorise-linnovation-numerique-au-senegal), [Teranga Times](https://www.terangatimesn.com/Intelligence-artificielle-et-inclusion-linguistique-Les-laureats-du-Kiriku-Voice-Challenge-recompenses-a-Dakar_a9643.html) |
| 2. Public et problème | Développeurs, start-up, services publics. Problème visé : l'absence de modèles vocaux pour le wolof, le pulaar et le sérère. L'État veut transformer les prototypes en services durables. | Déclaré | [Dakaractu](https://www.dakaractu.com/IA-et-langues-nationales-l-Etat-veut-transformer-les-prototypes-du-Kiriku-Challenge-en-services-durables_a277134.html) |
| 3. Technologies | M-Kiriku-ASR est un réglage fin d'`openai/whisper-large-v3`. | Déclaré (extrait de la fiche) | [HF M-Kiriku-ASR](https://huggingface.co/AIHubSN/M-Kiriku-ASR) |
| | Whisper « large » : 1 550 millions de paramètres ; code et poids sous licence MIT. | Vérifié | [github.com/openai/whisper](https://github.com/openai/whisper) |
| | Le modèle accepte des jetons de langue propres (`<\|wo\|>`, `<\|pu\|>`, `<\|se\|>`). La synthèse est un modèle VITS au format Coqui TTS 0.19 (`model.pth` et `config.json`), qui tourne sur processeur. | Vérifié (code d'un tiers) | [tewlu-kaddu, kiriku_models.py](https://github.com/MaDi-12/tewlu-kaddu/blob/main/backend/kiriku_models.py) |
| | Kiriku-Wolof-TTS : architecture VITS, 22 050 Hz. | Déclaré (extrait de la fiche) | [HF Kiriku-Wolof-TTS](https://huggingface.co/AIHubSN/Kiriku-Wolof-TTS) |
| 4. Langues et qualité | M-Kiriku-ASR, taux d'erreur de mots publiés par la fiche : wolof 16,34 %, pulaar 45,28 %, sérère 42,99 %, global 27,71 %. Un chiffre de 8,56 % pour le wolof circule aussi ; d'après un extrait, ce serait le taux d'erreur de caractères de la fiche, pris pour un taux d'erreur de mots. | Déclaré (extrait) ; contradiction signalée | [HF M-Kiriku-ASR](https://huggingface.co/AIHubSN/M-Kiriku-ASR), [arXiv 2601.09716](https://arxiv.org/abs/2601.09716) |
| | Kiriku-Wolof-ASR : taux d'erreur non lu. Un chiffre de 20,70 % circule sur LinkedIn, sans auteur identifiable avec certitude : à ne pas reprendre. | Non disponible | — |
| | Synthèse vocale : aucune mesure de qualité publiée trouvée. Pas de voix sérère : un lauréat répond en wolof aux messages en sérère. | Non disponible (mesure) ; Vérifié (absence de voix sérère, d'après le README du lauréat) | [tewlu-kaddu README](https://github.com/MaDi-12/tewlu-kaddu) |
| 5. Données et vérification | 210 heures collectées et annotées avec le Centre de linguistique appliquée de Dakar (CLAD) : 150 h pour la reconnaissance, 60 h pour la synthèse. | Déclaré | [Le Soleil](https://lesoleil.sn/actualites/technologie/kiriku-voice-challenge-des-modeles-dia-developpes-pour-les-langues-nationales/), [RTS](https://www.rts.sn/actualite/detail/a-la-une/ia-et-langues-nationales-le-kiriku-voice-challenge-valorise-linnovation-numerique-au-senegal) |
| | La fiche est incohérente : son tableau donne 88,27 h de wolof, 25,21 h de pulaar et 33,87 h de sérère (environ 150 h), sa présentation 34,9 h, 16,2 h et 24,3 h. Environ 90 h viennent d'enregistrements Kallaama non relus par des linguistes, fusionnés avec des corpus publics (dont Google FLEURS). | Déclaré (extrait) | [HF M-Kiriku-ASR](https://huggingface.co/AIHubSN/M-Kiriku-ASR) |
| | Pour la fiche de synthèse, la taille du jeu de données, le nombre de voix et la licence des données ne sont pas renseignés ; la fiche demande de les compléter avant toute diffusion externe. | Déclaré (extrait) | [HF Kiriku-Wolof-TTS](https://huggingface.co/AIHubSN/Kiriku-Wolof-TTS) |
| 6. Rapidité, coût, expérience | Aucune mesure publiée. Le lauréat charge un seul modèle à la fois en mémoire, sur processeur ou puce Apple. | Non disponible (mesure) ; Vérifié (code) | [kiriku_models.py](https://github.com/MaDi-12/tewlu-kaddu/blob/main/backend/kiriku_models.py) |
| | Teranga tourne sur l'offre Render Starter (0,5 processeur, 512 Mo) : impossible d'y faire tourner un modèle de la taille de Whisper large. | Vérifié | `docs/INFRASTRUCTURE.md`, ligne 12 |
| 7. Modèle économique et licence | Financement public et diplomatique (Sen Hub IA). Diffusion « en libre accès » annoncée. **Licence exacte des quatre modèles : non lue.** Hypothèse à vérifier : la lecture de `HF_TOKEN` par le lauréat pourrait signaler un accès soumis à conditions. | Déclaré ; Non disponible (licence) ; Hypothèse (accès) | [Le Soleil](https://lesoleil.sn/actualites/technologie/kiriku-voice-challenge-des-modeles-dia-developpes-pour-les-langues-nationales/) |
| 8. Partenariat ou intégration | Les organisateurs annoncent une phase de tests en conditions réelles et cherchent des partenaires : Teranga peut se proposer comme terrain de test. Intégration technique éprouvée par un tiers (Whisper plus Coqui). Hébergement externe nécessaire. | Déclaré (phase de test) ; Hypothèse (offre de Teranga) | [allAfrica](https://fr.allafrica.com/stories/202610160715.html) |
| 9. Forces, limites, enseignements | **Forces** : seul ensemble ouvert trouvé qui couvre le wolof, le pulaar et le sérère en reconnaissance ; soutien de l'État ; communauté de développeurs. **Limites** : erreurs élevées en pulaar et en sérère, licence floue, fiches incohérentes, pas de voix sérère, accès au calcul cité comme difficulté ([Osiris](https://www.osiris.sn/ia-et-langues-nationales-l-etat-veut-transformer-les-prototypes-du-kiriku.html), Déclaré). **Pour Teranga** : candidat n° 1 du banc vocal, à condition d'une licence écrite. | Synthèse | — |

## 2. Soynade Research et les technologies Oolel

| Point | Constat | Statut | Source |
|---|---|---|---|
| 1. Fonctionnalités disponibles | Organisation GitHub de 5 dépôts publics : `oolel-translator` (fabrique de données de traduction synthétiques vers le wolof avec MS-Swift et vLLM), `oolel-embed` (marqué « WORK IN PROGRESS »), `oolel-trainer`, `open-hub`, `.github`. | Vérifié | [github.com/soynade-research](https://github.com/soynade-research) |
| | `Oolel-Small-v0.1` existe : c'est le modèle par défaut cité par `oolel-translator` (`--model_type qwen2_5`). | Vérifié | [oolel-translator](https://github.com/soynade-research/oolel-translator) |
| | Oolel-Embed : recherche de documents en français à partir de questions parlées en wolof, sans transcription intermédiaire (encodeur HuBERT et Qwen3-Embedding) ; modèle `soynade-research/Oolel-Embed` ; article arXiv 2602.19991. | Vérifié (README) | [oolel-embed](https://github.com/soynade-research/oolel-embed) |
| | Modèles Hugging Face : `Oolel-v0.1` (LLM wolof, base Qwen 2.5, annoncé le 15 décembre 2024) ; `Oolel-Corrector` (remet en orthographe standard le wolof écrit sur les réseaux sociaux, sans toucher aux passages en français ou en anglais ; avril 2026) ; `Oolel-Voices` (synthèse wolof et wolof-français, clonage de voix, mars 2026) ; `Wolof-HuBERT-CTC` (reconnaissance, environ 94,4 millions de paramètres) ; `oolel-lit-gemma` (environ 0,3 milliard, base gemma-3-270m-it). | Déclaré (extraits) ; dates d'après le recensement (Vérifié, secondaire) | [HF soynade-research](https://huggingface.co/soynade-research), [X, 15/12/2024](https://x.com/soynade/status/1868388486954504280), [recensement](https://github.com/DerXter/State-of-NLP-Research-in-Senegal) |
| | API Soynade, d'après un projet tiers : base `https://api.soynade.ai/v1` ; routes `/v1/audio/transcriptions` (wolof parlé vers texte wolof), `/v1/audio/translations` (wolof parlé vers anglais), `/v1/translations`, `/v1/text-to-speech` (renvoie un WAV) ; modèles `oolel-speech-v1` et `Oolel-Voices` ; clé créée dans la console. Ce projet n'a été testé qu'avec des réponses enregistrées. | Vérifié (README d'un tiers) ; fonctionnement Déclaré | [DemePS/WaxalAgent](https://github.com/DemePS/WaxalAgent) |
| | Le site affiche les menus « API pricing », « Studio early access » et « Console ». La démo de synthèse est limitée à 500 caractères par requête. Oolel Studio : outil sans code pour la voix, le doublage, les sous-titres et la traduction. | Déclaré (extrait) | [soynade.ai](https://soynade.ai/), [démo](https://soynade.ai/demo/oolel-voices), [UNICEF Venture Fund](https://www.unicefventurefund.org/portfolio/soynade-research) |
| 2. Public et problème | Langues orales d'Afrique de l'Ouest, usage hors ligne, développement communautaire ; public annoncé : des chercheurs aux agriculteurs. | Vérifié (profil GitHub) | [soynade-research/.github](https://github.com/soynade-research/.github) |
| 3. Technologies | Qwen 2.5 (Oolel-v0.1) ; HuBERT et Qwen3-Embedding (Oolel-Embed) ; MS-Swift et vLLM (traduction). | Vérifié (README) ; Déclaré (base d'Oolel-v0.1) | voir lignes ci-dessus |
| | LLM vocal : HuBERT pré-entraîné sur du wolof puis relié à un LLM, réglé à partir de Qwen2.5 3B (LORIA/CNRS et Soynade, septembre 2025). | Déclaré (extrait) | [arXiv 2509.15362](https://arxiv.org/abs/2509.15362), [soynade.ai](https://soynade.ai/research/speech-llm-wolof) |
| 4. Langues et qualité | Reconnaissance : 35,65 % d'erreurs de mots après pré-entraînement continu, contre 39,48 % pour HuBERT de base et 41,11 % pour un modèle africain entraîné de zéro sur 65 000 h. | Déclaré (auteurs, extrait) | [arXiv 2509.15362](https://arxiv.org/abs/2509.15362) |
| | Wolof-HuBERT-CTC : environ 36 % d'erreurs de mots selon la fiche, d'où le conseil de traiter les transcriptions comme des brouillons. | Déclaré (cité par un tiers) | [ordomatics/oolel](https://github.com/ordomatics/oolel) |
| | Banc indépendant AI4Wolof, traduction, « score wolof » de 0 à 1 dont la méthode n'est pas décrite : Oolel-v0.1 = 0,450 (8e sur 13), contre gemini-2.0-flash-exp 0,685, claude-3-5-sonnet-latest 0,663, chatgpt-4o-latest 0,658. Anciens modèles, métrique opaque : indice faible. | Vérifié (lu ; scores déclarés par l'auteur du banc) | [github.com/dofbi/AI4Wolof](https://github.com/dofbi/AI4Wolof) |
| | Article d'Orange : Oolel-v0.1 n'a ni données d'entraînement publiques ni évaluation détaillée ; il fait jeu égal en wolof mais reste en dessous des autres modèles ouverts dans la plupart des autres compétences. | Déclaré (extrait) | [arXiv 2610.20824](https://arxiv.org/abs/2610.20824) |
| | La page UNICEF affirme qu'Oolel « dépasse les grands modèles commerciaux en qualité de traduction » : affirmation non démontrée ici. | Déclaré | [UNICEF Venture Fund](https://www.unicefventurefund.org/story/building-ai-speaks-wolof-reclaiming-digital-future-west-africa) |
| 5. Données et vérification | Jeux de données : `Wolof-ASR-Data` (dont environ 33,6 h tirées de Kallaama), `Wolof-Non-Standard-Orthography` (synthétique, généré avec Oolel), `FineWeb2-HQ-50k-Wolof` (synthétique), données de traduction parlée en bambara. Licence affichée pour certains : cc-by-sa-4.0. Contrôle humain : Non disponible. | Déclaré (extraits) | [HF datasets](https://huggingface.co/datasets/soynade-research/Wolof-ASR-Data), [recensement](https://github.com/DerXter/State-of-NLP-Research-in-Senegal) |
| 6. Rapidité, coût, expérience | Une passerelle tierce hébergée sur Modal, sur processeur, mesure environ 20 s de synthèse pour une phrase courte et environ une minute de réveil après 5 minutes d'inactivité ; transcription limitée à 25 Mo et 10 minutes par fichier. Tarifs de l'API : non lus. | Déclaré (mesures d'un tiers) ; Non disponible (tarifs) | [ordomatics/oolel](https://github.com/ordomatics/oolel) |
| 7. Modèle économique et licences | Start-up fondée en 2024 à Dakar par Dioula Doucouré et Yaya Sy ; 40 050 USD du UNICEF Venture Fund ; API payante et Studio. | Déclaré (extrait) | [UNICEF Venture Fund](https://www.unicefventurefund.org/portfolio/soynade-research) |
| | Licences du code : AGPL-3.0 pour `oolel-embed`, `oolel-trainer` et `open-hub`. `oolel-translator` se contredit : barre latérale AGPL-3.0, README « MIT ». | Vérifié | [github.com/soynade-research](https://github.com/soynade-research) |
| | Licences des modèles : Oolel-v0.1 en `apache-2.0` (ancien commit de la fiche et copie GGUF) ; Oolel-Voices en `agpl-3.0` ; oolel-lit-gemma en AGPL-3.0. Un tiers écrit que « les modèles Oolel sont sous AGPL-3.0 ». Les licences varient donc d'un modèle à l'autre : à relire une par une. | Déclaré (extraits) ; contradiction signalée | [HF Oolel-v0.1, commit 97a4d7f](https://huggingface.co/soynade-research/Oolel-v0.1/commit/97a4d7fe2b7856257c32b3d39e1bb85c2c8e1062), [HF Oolel-Voices README](https://huggingface.co/soynade-research/Oolel-Voices/blob/main/README.md), [ordomatics/oolel](https://github.com/ordomatics/oolel) |
| 8. Partenariat ou intégration | API HTTP simple à appeler depuis Flask, avec une clé. Le projet tiers prévient que tout ce que disent les personnes est envoyé à Soynade : il faut donc un contrat de traitement des données. Les poids sous AGPL imposent une revue juridique si Teranga les héberge (le dépôt Teranga n'a pas de fichier LICENSE). | Vérifié (README d'un tiers ; absence de LICENSE) ; Hypothèse (portée de l'AGPL) | [WaxalAgent](https://github.com/DemePS/WaxalAgent) |
| 9. Forces, limites, enseignements | **Forces** : la gamme la plus complète (LLM, voix, correction d'orthographe, recherche parole vers documents), du code publié, une API. **Limites** : wolof seulement pour l'instant, taux d'erreur élevés en reconnaissance, licences mixtes, peu d'évaluation publique. **Pour Teranga** : Oolel-Corrector pourrait normaliser le wolof écrit des utilisateurs avant de choisir les repères (Hypothèse, à tester) ; l'API est candidate au banc vocal. | Synthèse | — |

## 3. Andakia et l'assistant AWA

| Point | Constat | Statut | Source |
|---|---|---|---|
| 1. Fonctionnalités disponibles | API AWA annoncée comme disponible le 2 novembre 2024. | Déclaré | [X @Andakia_ai](https://x.com/Andakia_ai/status/1852509729655799929) |
| | Modules : transcription (d'une langue africaine vers le français ou l'anglais), synthèse vocale, analyse de la langue, indexation de contenu ; offre « Développeur » ; déploiement dans le nuage ou sur place ; documentation annoncée. | Déclaré (extrait) | [andakia.tech](https://www.andakia.tech/), [FAQ](https://www.andakia.tech/faq/) |
| | Kit Python généré avec Stainless, sous licence Apache-2.0, signalé comme « staging » : seule la connexion est documentée, la documentation renvoie à `docs.andakia.com`. Il s'agit d'une copie miroir (`backup-andakia`). | Vérifié (miroir) | [backup-andakia/andakia-python](https://github.com/backup-andakia/andakia-python) |
| | En 2026, Andakia « finalise le lancement » d'Awa en wolof et en pulaar, au téléphone et sur le web. Un modèle « Awa-Milkyway » a été annoncé mais pas publié. | Déclaré ; Vérifié (recensement secondaire) | [Europe-infos](https://www.europe-infos.fr/actualites/11487/a-dakar-andakia-finalise-awa-ia-en-wolof-et-pulaar-au-telephone-et-sur-le-web-ce-que-la-start-up-doit-affronter/), [Africa Business Index, 02/09/2026](https://theafricabusinessindex.com/2026/09/02/le-senegal-lance-awa-une-ia-capable-de-comprendre-le-wolof-et-le-pulaar/), [recensement](https://github.com/DerXter/State-of-NLP-Research-in-Senegal) |
| 2. Public et problème | Personnes peu alphabétisées ou ne parlant pas français ; entreprises. Usages envisagés : commander un taxi, envoyer de l'argent, faire une démarche. | Déclaré | [We Are Tech](https://www.wearetech.africa/fr/fils/tech-stars/avec-l-ia-alioune-badara-mbengue-leve-les-barrieres-linguistiques-au-senegal), [Forbes Afrique](https://forbesafrique.com/portrait-alioune-badara-mbengue/) |
| 3. Technologies | Non disponible. Les copies miroirs de `transformers` et `VietASR` laissent penser à un travail sur la reconnaissance vocale (Hypothèse). Un dépôt `awafoods-mcp` existe, contenu non lisible. | Non disponible ; Hypothèse | [recherche GitHub](https://github.com/search?q=andakia&type=repositories) |
| 4. Langues et qualité | Wolof ; pulaar en 2026 ; haoussa annoncé en 2024. Aucune évaluation indépendante. Un « panel de 200 personnes » est cité. Le fondateur reconnaît que l'orthographe du wolof fait débat. | Déclaré | [TRT Afrika](https://www.trtafrika.com/english/article/18244712), [Osiris](https://osiris.sn/awa-l-intelligence-artificielle-qui-parle-le-wolof-du-senegal.html) |
| 5. Données et vérification | Des centaines d'heures d'audio wolof collectées et annotées par l'équipe. Contrôle de qualité : Non disponible. | Déclaré | [We Are Tech](https://www.wearetech.africa/fr/fils/tech-stars/avec-l-ia-alioune-badara-mbengue-leve-les-barrieres-linguistiques-au-senegal) |
| 6. Rapidité, coût, expérience | Non disponible. | Non disponible | — |
| 7. Modèle économique et licences | Tarifs selon l'usage, grille sur demande. Entreprise fondée en 2024 par Alioune Badara Mbengue et Pape Gorgui Ndoye ; en couverture de Forbes Afrique (n° 91, mai-juin 2026). Modèles propriétaires (Hypothèse). | Déclaré (extrait) ; Hypothèse | [FAQ](https://www.andakia.tech/faq/), [Forbes Afrique](https://forbesafrique.com/produit/forbes-afrique-edition-de-mai-juin-2026-i-a-la-une-30-under-30-powerlist-2026-i-business-de-linfluence/) |
| 8. Partenariat ou intégration | API commerciale sur devis ; un déploiement sur place est annoncé, ce qui est intéressant pour la confidentialité des voix. | Déclaré | [FAQ](https://www.andakia.tech/faq/) |
| 9. Forces, limites, enseignements | **Forces** : produit pensé pour l'oral et le téléphone ; notoriété. **Limites** : pas de documentation ni de mesure publique, lancement 2026 encore annoncé comme « en cours de finalisation ». **Pour Teranga** : demander une clé d'essai pour le banc et un engagement écrit sur la conservation des voix. | Synthèse | — |

## 4. Institut des Algorithmes du Sénégal (IAS)

| Point | Constat | Statut | Source |
|---|---|---|---|
| 1. Fonctionnalités disponibles | Formations : ateliers « IA générative au service des métiers », plateforme KOCC, programme RENFOR'IA avec Pace Senegal. PAS Challenge 2026 à l'UCAD (102 équipes de 9 pays) et diagnostic de maturité IA pour les organisations (21 octobre 2026). | Déclaré (extraits) | [ias.sn](https://www.ias.sn/nos-formations), [kocc.ias.sn](https://kocc.ias.sn/), [Socialnetlink](https://www.socialnetlink.org/2026/10/21/pas-challenge-2026-diagnostic-maturite-ia-senegal/) |
| 2. Public et problème | Élèves, étudiants, enseignants, entreprises, décideurs, start-up ; former des talents de la donnée. | Déclaré | [ias.sn](https://www.ias.sn/nos-formations) |
| 3. Technologies | Non disponible. Le fondateur, Ndiaye Dia, est aussi co-initiateur de la start-up d'IA générative Jàngat.ai. | Déclaré | [APS](https://aps.sn/intelligence-artificielle-la-statistique-derriere-la-magie/) |
| 4. Langues et qualité | Aucune offre en langues nationales trouvée. | Non disponible | — |
| 5. Données et vérification | Sans objet. | — | — |
| 6. Rapidité, coût, expérience | Non disponible. | Non disponible | — |
| 7. Modèle économique et licences | Structure créée en 2020 ; tarifs des formations non lus. | Déclaré (extrait) ; Non disponible | [ias.sn](https://www.ias.sn/nos-formations) |
| 8. Partenariat ou intégration | Pas de brique à intégrer. Piste : recruter par l'IAS des évaluateurs ou des annotateurs pour le banc (Hypothèse). | Hypothèse | — |
| 9. Forces, limites, enseignements | Acteur de formation et d'animation, pas concurrent de Teranga. Le nom « KOCC » ressemble à l'assistant « COOC/Kocc » de Jangalma : **aucun lien établi**. | Synthèse | — |

## 5. Jokalante et le projet NAFOORE

| Point | Constat | Statut | Source |
|---|---|---|---|
| 1. Fonctionnalités disponibles | NAFOORE (« utile » en pulaar) : informations climatiques et conseils agricoles par radio, SMS, réseaux sociaux et appels vocaux. Depuis 2024, robot conversationnel vocal à IA générative, adapté à la météo, au sol et à la culture (projet du FID, juin 2024 à janvier 2026). Saaytu Mbay : assistant vocal sur WhatsApp. Serveur vocal interactif, sans internet. | Déclaré | [FID](https://fundinnovation.dev/en/projects/voice-ai-chatbot-provides-farming-advice-senegal), [Leral](https://www.leral.net/Ndeye-Amy-Kebe-Jokalante-l-information-agricole-en-sept-langues_a408135.html), [AI Hub for Development](https://aihubfordevelopment.org/innovators/ndeye-amy-kebe) |
| | Le catalogue cite FlowAgri, Fidelia CRM, Écho, Saaytu Mbay, Jokalante Connect et une « API voix et NLP ». | Déclaré (extrait) | [jokalante.com](https://jokalante.com/) |
| 2. Public et problème | Agriculteurs, pêcheurs et éleveurs ; entreprises et agences de l'État (collecte de données rurales). | Déclaré | [jokalante.com](https://jokalante.com/agencesdeletat/) |
| 3. Technologies | Le corpus Kallaama sert à entraîner leurs modèles de reconnaissance et de synthèse ; les modèles utilisés ne sont pas connus. | Déclaré ; Non disponible | [Leral](https://www.leral.net/Ndeye-Amy-Kebe-Jokalante-l-information-agricole-en-sept-langues_a408135.html) |
| 4. Langues et qualité | Wolof, sérère, pulaar, diola, mandingue, français, anglais (le site parle de « 6 langues locales »). Qualité : Non disponible. | Déclaré | [Leral](https://www.leral.net/Ndeye-Amy-Kebe-Jokalante-l-information-agricole-en-sept-langues_a408135.html) |
| 5. Données et vérification | **Kallaama** (projet mené par Jokalante, avec Orange Innovation et l'École polytechnique de Thiès, financé par le Lacuna Fund en 2023) : 125 h transcrites (wolof 55 h, pulaar environ 32 h, sérère 38 h), dont environ 35 h vérifiées par des experts ; licence **CC-BY-4.0** ; article RAIL 2024. | Vérifié (chiffres déclarés par les auteurs) | [gauthelo/kallaama-speech-dataset](https://github.com/gauthelo/kallaama-speech-dataset) |
| 6. Rapidité, coût, expérience | Portée annoncée : plus de 41 000 agriculteurs touchés entre 2020 et 2022 ; plus de 200 000 producteurs profilés ; plus de 200 radios partenaires. | Déclaré | [Leral](https://www.leral.net/Ndeye-Amy-Kebe-Jokalante-l-information-agricole-en-sept-langues_a408135.html), [AI Hub for Development](https://aihubfordevelopment.org/innovators/ndeye-amy-kebe) |
| 7. Modèle économique et licences | Entreprise sociale fondée en 2016 par Ndèye Amy Kébé ; clients publics et privés ; soutiens cités : I&P, Teranga Capital, FID, AI Hub for Sustainable Development (filière vocale en pulaar, essai avec 300 agriculteurs). | Déclaré | [IETP](https://www.ietp.com/en/secteur-dactivit%C3%A9/digital-tech), [AI Hub for Development](https://aihubfordevelopment.org/innovators/ndeye-amy-kebe) |
| 8. Partenariat ou intégration | Le corpus Kallaama est réutilisable (en citant les auteurs) pour **tester** des modèles. Attention : M-Kiriku et Soynade s'en servent déjà pour l'entraînement, d'où un risque de fuite entre entraînement et test. L'« API voix et NLP » est à demander. | Vérifié (licence) ; Hypothèse (fuite) | [kallaama](https://github.com/gauthelo/kallaama-speech-dataset) |
| 9. Forces, limites, enseignements | **Forces** : terrain rural, multicanal, pas seulement internet. **Limites** : agriculture hors du cœur de Teranga, pas de mesure publique. **Pour Teranga** : le canal vocal et WhatsApp, plutôt que le seul web, est la norme chez les acteurs qui touchent les non-lecteurs. | Synthèse | — |

## 6. Sunu SOUBA (emploi et mise en relation)

| Point | Constat | Statut | Source |
|---|---|---|---|
| 1. Fonctionnalités disponibles | Analyse des compétences des candidats et des besoins des recruteurs, recommandations par apprentissage automatique ; Sunu Souba Lab (missions pratiques corrigées, certification). | Déclaré | [We Are Tech](https://www.wearetech.africa/fr/fils/solutions/senegal-sunu-souba-utilise-l-ia-pour-connecter-chercheurs-d-emploi-et-recruteurs), [Notre Voix](https://www.notrevoix.info/info/articles/sunu-souba-la-solution-senegalaise-qui-reinvente-l-acces-a-l-emploi-en-afrique-grace-a-l-intelligence-des-donnees) |
| 2. Public et problème | Chercheurs d'emploi et recruteurs. Contexte cité : chômage élargi de 23,3 % au 4e trimestre 2025 selon l'ANSD. | Déclaré | [We Are Tech (EN)](https://www.wearetech.africa/en/fils-uk/solutions/sunu-souba-leverages-ai-to-improve-hiring-efficiency-in-senegal) |
| 3. Technologies | Django et React.js ; projet commencé le 21 février 2026. Modèles : Non disponible. | Déclaré (extrait) | [Devpost](https://devpost.com/software/sunu-souba) |
| 4. Langues et qualité | Non disponible. | Non disponible | — |
| 5. Données et vérification | Non disponible. | Non disponible | — |
| 6. Rapidité, coût, expérience | Aucun chiffre d'utilisateurs ou de placements. | Non disponible | — |
| 7. Modèle économique et licences | Né au sein du groupe de réflexion FATI (Mouhammadou Dia, Abdou Ba). « Champion » des prix SMSI 2026, catégorie emploi en ligne (Genève, 6 au 10 juillet 2026). Modèle économique : Non disponible. | Déclaré | [RTS](https://www.rts.sn/actualite/detail/a-la-une/smsi-2026-et-ai-for-good-le-senegal-brille-sur-la-scene-mondiale-de-linnovation-numerique-et-de-lintelligence-artificielle), [Ndarinfo](https://www.ndarinfo.com/Deux-Champions-mondiaux-et-six-nominations-le-Senegal-dans-le-top-du-numerique-mondial-en-2026_a45568.html) |
| 8. Partenariat ou intégration | Faible : renvoi depuis une réponse « emploi » de Teranga si le service est public (Hypothèse, à faire valider par le propriétaire). | Hypothèse | [sunu-souba.com](https://www.sunu-souba.com/) (non lisible) |
| 9. Forces, limites, enseignements | Reconnaissance internationale, mais aucune donnée d'usage publique. **Pour Teranga** : ne pas promettre d'offres d'emploi ; renvoyer vers des services identifiés. | Synthèse | — |

## 7. Jangalma (éducation numérique)

| Point | Constat | Statut | Source |
|---|---|---|---|
| 1. Fonctionnalités disponibles | Fiches et exercices de la 6e à la terminale conformes au programme sénégalais (« plus de 3 000 fiches » sur le site, « plus de 2 000 contenus » sur l'App Store) ; assistant IA « COOC » (« Kocc » dans la presse) qui explique une leçon prise en photo ou une question écrite ou orale ; cours téléchargeables pour un usage hors ligne ; cours à domicile à Dakar. | Déclaré | [jangalma.net](https://jangalma.net/jangalma-app/), [Socialnetlink](https://www.socialnetlink.org/2025/05/10/jangalma-le-champion-senegalais-du-e-learning-qui-revolutionne-leducation-avec-lia/), [App Store](https://apps.apple.com/sn/app/jangalma/id6477892059) |
| 2. Public et problème | Élèves et parents ; inégalités d'accès à un enseignement de qualité. | Déclaré | [Osiris](https://osiris.sn/jangalma-le-champion-senegalais-du-e-learning-qui-revolutionne-l-education-avec.html) |
| 3. Technologies | Non disponible. | Non disponible | — |
| 4. Langues et qualité | Français (Hypothèse) ; qualité de l'assistant : Non disponible. | Hypothèse ; Non disponible | — |
| 5. Données et vérification | Contenus alignés sur le programme national. Relecture : Non disponible. | Déclaré | [jangalma.net](https://jangalma.net/jangalma-app/) |
| 6. Rapidité, coût, expérience | Nombre d'utilisateurs contradictoire : « 3 millions d'élèves » (site) contre plus de 150 000 utilisateurs et 400 enseignants (presse, mai 2025). | Déclaré ; contradiction signalée | [jangalma.net](https://jangalma.net/jangalma-app/), [Osiris](https://osiris.sn/jangalma-le-champion-senegalais-du-e-learning-qui-revolutionne-l-education-avec.html) |
| 7. Modèle économique et licences | Essai gratuit puis abonnement mensuel ou annuel, prix affichés dans l'application ; éditeur DIDACTIC CORPORATION SAS ; application iOS sortie le 18 février 2024 ; nommée aux prix SMSI 2026 (apprentissage en ligne). | Déclaré (extraits) | [CGS](https://jangalma.net/confidentialit%C3%A9.html), [mwm.ai](https://mwm.ai/apps/jangalma/6477892059), [RTS](https://www.rts.sn/actualite/detail/a-la-une/smsi-2026-et-ai-for-good-le-senegal-brille-sur-la-scene-mondiale-de-linnovation-numerique-et-de-lintelligence-artificielle) |
| 8. Partenariat ou intégration | Faible : hors du champ de Teranga. | Hypothèse | — |
| 9. Forces, limites, enseignements | Contenu ancré dans le programme national, version hors ligne. Chiffres d'audience contradictoires. **Pour Teranga** : le hors-ligne est une attente réelle du public sénégalais (Teranga a déjà un service worker). | Synthèse | — |

## 8. KadduCare (documentation médicale assistée par IA)

| Point | Constat | Statut | Source |
|---|---|---|---|
| 1. Fonctionnalités disponibles | **Seul fait trouvé** : KadduCare figure parmi les six projets sénégalais nommés aux prix SMSI 2026, catégorie e-santé (AL C7). La fonction « documentation médicale assistée par IA » indiquée dans la demande n'apparaît dans **aucune** source trouvée. | Déclaré (nomination) ; Non disponible (fonction) | [RTS](https://www.rts.sn/actualite/detail/a-la-une/smsi-2026-et-ai-for-good-le-senegal-brille-sur-la-scene-mondiale-de-linnovation-numerique-et-de-lintelligence-artificielle), [Pressafrik](https://www.pressafrik.com/Sommet-mondial-de-la-technologie-2026-le-Senegal-brille-avec-8-projets-retenus-et-des-distinctions-majeures-a-l-UIT_a308406.html) |
| 2 à 8 | Public, technologies, langues, données, coût, modèle économique, partenariat : aucune information trouvée (recherches sur « KadduCare », « Kaddu Care » et dans la base des prix SMSI). | Non disponible | — |
| 9. Enseignements | Ne pas confondre avec Tewlu Kaddu (2e du Kiriku Voice Challenge, commerce), Kaduceo (start-up de Toulouse) ou SunuDoctor (démonstration de prise de notes cliniques sur GitHub, données synthétiques). **Pour Teranga** : la santé est un domaine à haut risque ; rester sur l'orientation (page `/urgences`) et les repères vérifiés. | Synthèse | — |

## 9. AI-Karangué (sécurité routière)

| Point | Constat | Statut | Source |
|---|---|---|---|
| 1. Fonctionnalités disponibles | Alerte en moins de 2 secondes en cas de somnolence, de distraction ou d'usage du téléphone au volant, même sans connexion ; suivi en temps réel de la conduite et de la position. Gamme commerciale : caméras de bord IA avec aide à la conduite (ADAS) et surveillance du conducteur (DSM), traceurs GPS, enregistreurs mobiles, plateforme Karangué221. | Déclaré | [APS, 13/05/2026](https://aps.sn/ai-karangue-une-innovation-senegalaise-basee-sur-lintelligence-artificielle-pour-reduire-les-accidents-routiers/), [site produits](https://aikarangue.artbeaurescence.sn/en/products) |
| 2. Public et problème | Flottes privées et véhicules administratifs, puis transports publics ; transport, camionnage, mines, taxis. | Déclaré | [APS](https://aps.sn/ai-karangue-une-innovation-senegalaise-basee-sur-lintelligence-artificielle-pour-reduire-les-accidents-routiers/) |
| 3. Technologies | Matériel Streamax, traceurs Teltonika, plateforme Wialon ; analyse faite dans l'appareil, sans aller-retour vers un serveur. | Déclaré (extrait) | [site produits](https://aikarangue.artbeaurescence.sn/en/products) |
| 4. Langues et qualité | Alertes en langues nationales : Non disponible. Efficacité sur les routes sénégalaises : aucune évaluation indépendante. | Non disponible | — |
| 5. Données et vérification | Données de conduite produites par les appareils (Déclaré). | Déclaré | [SenePlus](https://www.seneplus.com/article/ai-karangue-linnovation-senegalaise-qui-veut-prevenir-les-accidents-routiers) |
| 6. Rapidité, coût, expérience | « Baisse de 42 % des incidents » sur des sites miniers (blog du vendeur) ; « plus de 70 % des accidents dus au facteur humain » (concepteur). Non vérifié. | Déclaré | [blog](https://aikarangue.artbeaurescence.sn/en/blog/mining-safety-ai), [APS](https://aps.sn/ai-karangue-une-innovation-senegalaise-basee-sur-lintelligence-artificielle-pour-reduire-les-accidents-routiers/) |
| 7. Modèle économique et licences | Vente aux entreprises par Art'Beau-Rescence SAS (fondée en 2022) ; prix de la meilleure jeune entreprise d'IA au GITEX Africa 2026 ; équipe liée à l'Université numérique Cheikh Hamidou Kane. | Déclaré | [À propos](https://aikarangue.artbeaurescence.sn/en/about), [Seneweb](https://www.seneweb.com/en/news/Technologie/gitex-morocco-2026-senegal-on-top-of-africa-thanks-to-ai-karangue_n_489313.html) |
| 8. Partenariat ou intégration | Hors du champ de Teranga. | Hypothèse | — |
| 9. Forces, limites, enseignements | Produit vendu et non prototype, d'après l'entreprise. Chiffres d'impact non vérifiés. **Pour Teranga** : pas de lien direct ; ne pas citer leurs chiffres dans les repères de sécurité routière. | Synthèse | — |

## 10. Vie Publique Sénégal (recherche d'informations publiques)

| Point | Constat | Statut | Source |
|---|---|---|---|
| 1. Fonctionnalités disponibles | Plus de 10 000 documents officiels (lois, décrets, rapports, Journal officiel) avec recherche plein texte ; actualités et dossiers ; Assemblée nationale ; Conseil des ministres ; organisation de l'État ; budget ; élections ; projets publics ; podcasts ; lettre d'information, RSS, notifications ; application Android et iOS. | Vérifié (README) | [Code-for-Senegal/vie-publique.sn](https://github.com/Code-for-Senegal/vie-publique.sn) |
| | Dans le code : page `/chatbot` « Assistant Vie Publique » (« Je peux vous aider à trouver des informations sur les documents officiels, les lois, et l'actualité du Sénégal ») qui relaie les questions vers un service externe (`CHATBOT_API_URL`). La page est en `noindex` et interdite aux robots. Son état en production : Non disponible. | Vérifié (code) | `server/api/chat.ts`, `app/components/ChatBot.vue`, `nuxt.config.ts` du dépôt |
| | Coorganisateur du Kiriku Voice Challenge. Un Space Hugging Face « Vie Publique » (compte `dofbi`) existe, sans lien officiel établi. | Déclaré | [APS](https://aps.sn/intelligence-artificielle-15-equipes-selectionnees-pour-developper-des-solutions-vocales-en-langues-nationales/), [HF Space](https://huggingface.co/spaces/dofbi/vie-publique) |
| 2. Public et problème | Citoyens ; transparence et accès à l'information publique. La fiche de l'application précise qu'elle n'est ni officielle, ni affiliée au gouvernement. | Vérifié (README) ; Déclaré (fiche de l'application) | [README](https://github.com/Code-for-Senegal/vie-publique.sn), [Google Play](https://play.google.com/store/apps/details?id=sn.viepublique.app&hl=en_US) |
| 3. Technologies | Nuxt 4, Directus, PostgreSQL, Redis, MinIO, Typesense, n8n ; « Mistral AI / OpenAI » pour la reconnaissance de texte et le résumé des documents ; hébergement sur VPS Hostinger avec Coolify et Cloudflare. | Vérifié (README) | [README](https://github.com/Code-for-Senegal/vie-publique.sn) |
| 4. Langues et qualité | Interface en français. Des « initiatives d'IA multilingue » figurent parmi les objectifs à financer. | Vérifié (README) | [README](https://github.com/Code-for-Senegal/vie-publique.sn) |
| 5. Données et vérification | L'origine exacte des documents et la façon de les collecter ne sont pas décrites dans le README. Les pages du site sont des résumés d'une communauté ; le texte du Journal officiel reste la référence. | Vérifié (absence d'information) | [README](https://github.com/Code-for-Senegal/vie-publique.sn) |
| 6. Rapidité, coût, expérience | « 59 000 utilisateurs actifs par mois » (README), alors qu'un article cite « environ 60 000 visiteurs uniques par mois » : deux mesures différentes. | Déclaré | [README](https://github.com/Code-for-Senegal/vie-publique.sn) |
| 7. Modèle économique et licences | Projet citoyen open source sous **GPL-3.0**, financé par des dons (GitHub Sponsors) ; dernier commit lu le 14 juillet 2026. | Vérifié | [LICENSE](https://github.com/Code-for-Senegal/vie-publique.sn) |
| 8. Partenariat ou intégration | Aucune API publique documentée. Les liens vers les pages de Vie Publique sont possibles en complément du texte officiel. Le code GPL-3.0 ne doit pas être recopié dans le code fermé de Teranga. Partenariat possible : flux des nouveaux textes (lois, décrets) pour signaler à Teranga les repères pratiques à revoir (Hypothèse). | Vérifié (licence) ; Hypothèse | — |
| 9. Forces, limites, enseignements | **Forces** : la base documentaire publique la plus large trouvée, code ouvert, acteur central du challenge Kiriku. **Limites** : indépendant (non officiel), sources des documents non décrites. **Pour Teranga** : bon allié pour tenir à jour les repères `practical_facts` (code du travail 2026, par exemple), en citant toujours le texte officiel. | Synthèse | — |

---

## Autres initiatives pertinentes découvertes

| Initiative | Ce qui est documenté | Licence / accès | Statut | Source |
|---|---|---|---|---|
| **Orange : modèles de langue wolof** (groupe français, actionnaire de Sonatel) | Modèles ouverts de 0,6 à 14 milliards de paramètres adaptés au wolof, évalués sur 63 tâches, essayés dans des services clients internes ; collection `Orange/wolof-lm` ; environ 222 000 consignes en wolof publiées (article du 14 octobre 2026). En 2024, Orange annonçait des modèles wolof et pulaar à partir de Whisper et Llama, avec OpenAI et Meta. | Usage **non commercial** annoncé : exclu pour la production de Teranga (voir les pistes) | Déclaré (extraits) | [arXiv 2610.20824](https://arxiv.org/abs/2610.20824), [Orange Newsroom](https://newsroom.orange.com/orange-to-expand-open-source-ai-models-to-african-regional-languages-for-digital-inclusion/), [CNBC](https://www.cnbc.com/2024/11/26/orange-partners-with-openai-meta-on-custom-african-language-ai-models.html) |
| **Meta Omnilingual ASR** (non sénégalais, mais il couvre les langues du Sénégal) | Reconnaissance vocale pour plus de 1 600 langues, dont `wol_Latn`, `fuc_Latn` (pulaar), `srr_Latn` (sérère), `dyo_Latn` (diola), `mnk_Latn` (mandingue), `snk_Latn` (soninké). Taux d'erreur de caractères publiés par Meta pour le système 7B-LLM-ASR : wolof 11,1 (50,4 h d'entraînement), pulaar 32,2 (29,0 h), sérère 30,8 (32,5 h). Modèles de 300 M à 7 B paramètres (le 7B demande environ 17 Gio de mémoire graphique). | Code **et modèles sous Apache 2.0** ; corpus CC-BY-4.0 | Vérifié (dépôt lu ; chiffres déclarés par Meta, domaine des jeux de test non connu) | [facebookresearch/omnilingual-asr](https://github.com/facebookresearch/omnilingual-asr) (README, LICENSE, `per_language_results_table_7B_llm_asr.csv`) |
| **ElevenLabs Scribe** (service commercial) | Le wolof figure dans la liste des langues de transcription ; le pulaar non. | Payant | Vérifié (dépôt officiel) | [elevenlabs/skills](https://github.com/elevenlabs/skills/blob/main/speech-to-text/references/transcription-options.md) |
| **Google WAXAL** | Corpus de parole africain ouvert, publié en février 2026 ; le nombre de langues varie selon les sources (21, 24 ou 27). GalsenAI en a republié une version wolof réalignée, car l'audio et le texte du wolof étaient décalés. | CC-BY-4.0 | Déclaré (extraits) | [Google Research](https://research.google/blog/waxal-a-large-scale-open-resource-for-african-language-speech-technology/), [arXiv 2602.02734](https://arxiv.org/abs/2602.02734), [HF galsenai/WaxalNLP](https://huggingface.co/datasets/galsenai/WaxalNLP) |
| **GalsenAI** (communauté) | 17 dépôts : Wolof-TTS (MIT), Wolof-NMT, Wolof-ASR, textes pour Common Voice (CC-BY-SA-4.0), waxal-project (CC0-1.0). Le modèle `galsenai/xTTS-v2-wolof` (septembre 2024) part de XTTS, dont la licence Coqui interdit l'usage commercial. | Variable | Vérifié (organisation GitHub) ; Déclaré (licence XTTS, extrait) | [github.com/Galsenaicommunity](https://github.com/Galsenaicommunity), [HF coqui/XTTS-v2](https://huggingface.co/coqui/XTTS-v2/blob/main/LICENSE.txt) |
| **LAfricaMobile** (Dakar, fondée en 2014) | API de synthèse vocale (voix wolof, bambara, lingala, dioula), de traduction du français et de transcription. | Commerciale, tarifs non lus | Déclaré (extraits) | [developers.lafricamobile.com](https://developers.lafricamobile.com/), [produit TTS](https://lafricamobile.com/en/produit-tts/) |
| **CONCREE Adia_TTS** | Synthèse wolof à partir de parler-tts-mini-multilingual. | `apache-2.0`, lu sur un instantané de demande de fusion | Déclaré (extrait) | [HF CONCREE/Adia_TTS](https://huggingface.co/CONCREE/Adia_TTS) |
| **Tewlu Kaddu** (2e du Kiriku Voice Challenge) | Tenue de comptes par notes vocales en wolof, pulaar ou sérère sur WhatsApp et Telegram. Reconnaissance M-Kiriku-ASR, synthèse Kiriku wolof et pulaar, compréhension par un LLM via OpenRouter (température 0, réponse JSON imposée). Chiffrement et consentement prévus mais pas encore faits. | Licence non indiquée | Vérifié (dépôt cloné, dernier commit le 11 octobre 2026) | [MaDi-12/tewlu-kaddu](https://github.com/MaDi-12/tewlu-kaddu) |
| **Sunuchat** (3e du Kiriku Voice Challenge, École polytechnique de Thiès) | Assistant santé sur WhatsApp. Le projet annonce 47 documents officiels et 2 303 passages indexés (ministère de la Santé, PNLP, OMS, UNICEF), lecture d'ordonnances, pharmacies de garde. Le site parle de wolof et de français, la presse de wolof et de pulaar. | Non disponible | Déclaré (extraits) ; dépôt GitHub introuvable (404) lors de la lecture | [sunuchat.com](https://www.sunuchat.com/), [GitHub (404)](https://github.com/Alioukun221/Sunuchat_Voicebot) |
| **AI4Wolof** | Banc indépendant de LLM en wolof (traduction seulement), dont la métrique n'est pas expliquée. | MIT | Vérifié | [dofbi/AI4Wolof](https://github.com/dofbi/AI4Wolof) |
| **State-of-NLP-Research-in-Senegal** | Recensement vivant des ressources pour six langues nationales (lié à l'article arXiv 2601.09716) ; dernier commit le 21 août 2026. | MIT | Vérifié (source secondaire) | [DerXter/State-of-NLP-Research-in-Senegal](https://github.com/DerXter/State-of-NLP-Research-in-Senegal) |

---

## Pistes concrètes pour Teranga

Point de départ, vérifié dans le code de Teranga :

- transcription : `gpt-4o-transcribe` (`routes/stt.py`). Pour le wolof et le pulaar, la langue n'est pas imposée, car le commentaire du code dit que le modèle « ne connaît pas le wolof ni le pulaar » ;
- synthèse : `gpt-4o-mini-tts`, voix `cedar` (`routes/tts.py`) ;
- conversation vocale en temps réel : `gpt-realtime-2.1` (`routes/realtime.py`) ;
- langues acceptées : `fr`, `en`, `wo`, `ff` (`app.py`, `SAFE_LANG`).

Teranga a aussi une activité commerciale : liens partenaires `/go/<type>` et offres partenaires (`AGENTS.md`). **Toute licence « non commerciale » est donc exclue de la production.**

### Piste 1 (la plus prometteuse) : un banc vocal wolof et pulaar, hors production

But : décider sur des mesures, pas sur des annonces. Aucun résultat n'est donné ici, car rien n'a été mesuré.

- **Candidats pour la transcription** : `gpt-4o-transcribe` (système actuel), `AIHubSN/M-Kiriku-ASR` et `AIHubSN/Kiriku-Wolof-ASR`, l'API Soynade (`oolel-speech-v1`) ou `Wolof-HuBERT-CTC`, Meta `omniASR_LLM_*` (Apache 2.0), ElevenLabs Scribe (wolof seulement), l'API AWA d'Andakia (sur devis).
- **Jeu de test** : enregistrements faits pour Teranga avec le consentement écrit des personnes (questions réelles : transport, prix, démarches, Gorée, AIBD), plus la partie test de Kallaama (CC-BY-4.0, en citant les auteurs) et de WAXAL (CC-BY-4.0).
  - Écarter de la comparaison, ou signaler à part, les modèles qui ont pu voir Kallaama à l'entraînement (Kiriku, Soynade).
  - Une seule normalisation de l'orthographe pour tous les modèles ; le wolof sans orthographe fixe fausse le taux d'erreur de mots.
- **Mesures** :
  - taux d'erreur de mots et de caractères ;
  - temps de réponse de bout en bout (médiane et 95e centile, mesurés comme dans `services/latency.py`) ;
  - coût par minute ;
  - taux d'échec.
  - Le script va dans `scripts/`, avec un mode simulé sans réseau pour la CI, sur le modèle de `scripts/banc_v3.py`.
- **Synthèse vocale** : écoute à l'aveugle par au moins 5 locuteurs natifs par langue (wolof, pulaar), avec une grille simple : compréhension, naturel, prononciation des noms de lieux. Aucun score automatique présenté comme une « qualité ».
  - Candidats : `gpt-4o-mini-tts` (système actuel), `Kiriku-Wolof-TTS`, `Kiriku-Pulaar-TTS`, `Oolel-Voices` (ou l'API Soynade), `Adia_TTS`, LAfricaMobile.
- **Contraintes** :
  - L'offre Render actuelle (0,5 processeur, 512 Mo) ne peut faire tourner aucun de ces modèles : il faudrait une API ou un hébergement externe à processeur graphique, à chiffrer pendant le banc.
  - La synthèse et la transcription sont limitées par des quotas (`TTS_RATE_LIMIT`, `STT_RATE_LIMIT`) ; un fournisseur lent dégraderait la conversation vocale.
- **Barrière juridique** : aucun usage en production sans licence lue et conservée dans la PR, ni sans accord écrit sur les voix des utilisateurs (loi sénégalaise 2008-12 sur les données personnelles).

### Piste 2 : partenariat avec AI Hub Sénégal (Kiriku) et Vie Publique Sénégal

- **Kiriku** : les organisateurs annoncent des tests en conditions réelles et cherchent des partenaires (Déclaré). Teranga peut proposer d'être un terrain d'essai en échange de quatre choses :
  - une licence écrite permettant l'usage commercial ;
  - un accès à un hébergement des modèles ou une aide au calcul ;
  - une évaluation commune sur le jeu de test de Teranga ;
  - des retours d'erreurs anonymisés, seulement avec le consentement des utilisateurs.
- **Vie Publique** : lier les repères pratiques (`services/practical_facts.py`) au texte officiel et, en complément, à la page Vie Publique correspondante. Demander un flux des nouveaux textes pour savoir quand un repère « à vérifier » doit être revu. Ne pas recopier leur code (GPL-3.0).

### Piste 3 : API wolof spécialisée en complément (Soynade ou Andakia), seulement si le banc le justifie

- **Soynade** : API documentée par des tiers, simple à appeler en HTTP. **Andakia** : API sur devis, avec une option annoncée de déploiement sur place.
- Avant tout branchement : contrat de traitement des données, durée de conservation des voix, lieu d'hébergement, coût par minute. Le fournisseur reçoit tout ce que disent les utilisateurs.
- En option, à tester, ne pas supposer : `Oolel-Corrector` pour remettre en orthographe standard le wolof tapé par les utilisateurs avant le choix des lieux et des repères. À faire passer par `tests/test_ai_bench*.py` si cela touche le contexte de l'IA. Licence du modèle à lire.

### Autres enseignements (moins prioritaires)

- **Canal** : Jokalante, Andakia, Sunuchat et Tewlu Kaddu passent par WhatsApp, la voix ou le téléphone. Un canal WhatsApp pour Teranga reste une hypothèse : il faut évaluer le coût, les règles de Meta et la confidentialité.
- **Commerçants et transport** : Tewlu Kaddu (commerçants) et TekTalma (transport) visent des publics de Teranga. Un échange avec ces équipes pourrait éviter de refaire le même travail.
- **Orange `wolof-lm`** : utile au plus pour un banc interne de qualité du wolof écrit (usage non commercial annoncé), pas pour la production.
- **Honnêteté linguistique** : les acteurs sérieux présentent leurs transcriptions comme des brouillons et reconnaissent les débats d'orthographe. Teranga applique déjà la règle « ne pas inventer de mot wolof ou pulaar » (`services/language_quality.py`, `services/voice_quality.py`) ; garder cette ligne dans toute communication sur la voix.
- **Ne pas écrire** sur le site que Teranga est « meilleur » ou « moins bon » que Kiriku, Oolel ou AWA tant qu'aucune mesure n'existe.

## Méthode et limites

- **Outils** : WebSearch (extraits de moteur de recherche), WebFetch, et `git clone` de dépôts publics GitHub (Omnilingual ASR, State-of-NLP-Research-in-Senegal, Tewlu Kaddu, Vie Publique). Les fichiers téléchargés ont été lus sans exécuter aucun code.
- **Réseau de la session** : seuls `github.com` et `raw.githubusercontent.com` étaient lisibles.
  - Le proxy a refusé (403) `huggingface.co`, `hf-mirror.com`, `featherless.ai`, `www.osiris.sn`, `lesoleil.sn` et `aihubsenegal.com`.
  - WebFetch n'a pas pu résoudre (`ENOTFOUND`) `huggingface.co`, `featherless.ai`, `lesoleil.sn`, `www.osiris.sn`, `www.unicefventurefund.org`, `arxiv.org`, `soynade.ai`, `www.andakia.tech`, `jokalante.com`, `ai-hubsenegal.sn`, `www.vie-publique.sn`, `www.ias.sn`, `jangalma.net`, `aikarangue.artbeaurescence.sn`, `www.sunu-souba.com`, `www.sunuchat.com` et `aps.sn`.
  - Les autres sites cités (presse, LinkedIn, X, magasins d'applications, ITU) n'ont été consultés que par extraits de recherche et relèvent sans doute de la même restriction (Hypothèse).
  - La recherche par l'API GitHub est refusée dans cette session ; la recherche web de GitHub a été utilisée à la place.
- **Conséquence** : toutes les informations des fiches Hugging Face (licences, taux d'erreur, tailles) sont « Déclaré (extrait) ». Les extraits sont des résumés automatiques qui peuvent contenir des erreurs. Les contradictions trouvées sont signalées, pas tranchées.
- **Ce qui n'a pas été fait** : aucun service testé, aucun modèle téléchargé ni exécuté, aucun code privé audité, aucun score calculé ou inventé.
- **Pages à relire depuis un réseau normal avant toute décision** :
  - champ « License » des fiches `AIHubSN/*` et `soynade-research/*` ;
  - pages « API pricing » de soynade.ai ;
  - documentation et tarifs d'andakia.tech ;
  - fiche `Orange/wolof-lm` ;
  - fiche ITU de KadduCare ;
  - sites de Sunu SOUBA et de Jangalma.
- **Fraîcheur** : l'écosystème évolue vite (modèles Kiriku d'août 2026, résultats du challenge du 16 octobre 2026, article d'Orange du 14 octobre 2026). Ce document reflète l'état au 25 octobre 2026.

## Sources

État de lecture : **lu** = page ouverte et lue dans la session ; **extrait** = connue seulement par un extrait de recherche ; **non lisible** = ouverture tentée, sans succès.

### Dépôts et fichiers primaires (lus)

1. https://github.com/soynade-research (organisation, profil `.github`) — lu
2. https://github.com/soynade-research/oolel-translator — lu
3. https://github.com/soynade-research/oolel-embed — lu
4. https://github.com/soynade-research/open-hub — lu
5. https://github.com/ordomatics/oolel — lu (tiers)
6. https://github.com/DemePS/WaxalAgent — lu (tiers)
7. https://github.com/backup-andakia/andakia-python — lu (miroir)
8. https://github.com/backup-andakia/awafoods-mcp — lu (README absent)
9. https://github.com/search?q=andakia&type=repositories — lu
10. https://github.com/gauthelo/kallaama-speech-dataset — lu
11. https://github.com/Code-for-Senegal/vie-publique.sn — cloné et lu (README, LICENSE, `server/api/chat.ts`, `app/components/ChatBot.vue`, `nuxt.config.ts`)
12. https://github.com/MaDi-12/tewlu-kaddu — cloné et lu (README, `backend/kiriku_models.py`)
13. https://github.com/Birama-cloud/tektalma-ai — lu (projet du hackathon GOMYCODE ; lien avec le lauréat TekTalma non établi)
14. https://github.com/Alioukun221/Sunuchat_Voicebot — non lisible (404)
15. https://github.com/facebookresearch/omnilingual-asr — cloné et lu (README, LICENSE, CSV des résultats)
16. https://github.com/openai/whisper — lu
17. https://github.com/elevenlabs/skills/blob/main/speech-to-text/references/transcription-options.md — lu
18. https://github.com/Galsenaicommunity — lu
19. https://github.com/dofbi/AI4Wolof — lu
20. https://github.com/DerXter/State-of-NLP-Research-in-Senegal — cloné et lu (README, Datasets.md)
21. Code de Teranga : `routes/stt.py`, `routes/tts.py`, `routes/realtime.py`, `app.py`, `services/language_quality.py`, `services/voice_quality.py`, `docs/INFRASTRUCTURE.md`, `AGENTS.md` — lu

### Fiches de modèles et de données (Hugging Face, non lisibles : extraits)

22. https://huggingface.co/AIHubSN/M-Kiriku-ASR
23. https://huggingface.co/AIHubSN/Kiriku-Wolof-TTS
24. https://huggingface.co/soynade-research et https://huggingface.co/soynade-research/Oolel-v0.1
25. https://huggingface.co/soynade-research/Oolel-v0.1/commit/97a4d7fe2b7856257c32b3d39e1bb85c2c8e1062
26. https://huggingface.co/soynade-research/Oolel-Voices/blob/main/README.md
27. https://huggingface.co/soynade-research/Oolel-Corrector
28. https://huggingface.co/datasets/soynade-research/Wolof-ASR-Data
29. https://huggingface.co/datasets/soynade-research/Wolof-Non-Standard-Orthography
30. https://huggingface.co/CONCREE/Adia_TTS
31. https://huggingface.co/coqui/XTTS-v2/blob/main/LICENSE.txt
32. https://huggingface.co/datasets/galsenai/WaxalNLP
33. https://huggingface.co/spaces/dofbi/vie-publique
34. https://featherless.ai/models/soynade-research/Oolel-v0.1 — non lisible (extrait)

### Sites officiels (non lisibles : extraits)

35. https://ai-hubsenegal.sn/en/portfolios/senhubia/
36. https://soynade.ai/ , https://soynade.ai/research/oolel-voices-tts , https://soynade.ai/demo/oolel-voices , https://soynade.ai/research/speech-llm-wolof
37. https://www.andakia.tech/ , https://www.andakia.tech/faq/
38. https://jokalante.com/ , https://jokalante.com/agencesdeletat/
39. https://www.ias.sn/nos-formations , https://kocc.ias.sn/
40. https://jangalma.net/jangalma-app/ , https://jangalma.net/confidentialit%C3%A9.html
41. https://aikarangue.artbeaurescence.sn/en/about , https://aikarangue.artbeaurescence.sn/en/products , https://aikarangue.artbeaurescence.sn/en/blog/mining-safety-ai
42. https://www.sunu-souba.com/ , https://devpost.com/software/sunu-souba
43. https://www.sunuchat.com/
44. https://www.vie-publique.sn/a-propos/qui-sommes-nous
45. https://developers.lafricamobile.com/ , https://lafricamobile.com/en/produit-tts/
46. https://www.unicefventurefund.org/portfolio/soynade-research , https://www.unicefventurefund.org/story/building-ai-speaks-wolof-reclaiming-digital-future-west-africa
47. https://fundinnovation.dev/en/projects/voice-ai-chatbot-provides-farming-advice-senegal
48. https://aihubfordevelopment.org/innovators/ndeye-amy-kebe
49. https://newsroom.orange.com/orange-to-expand-open-source-ai-models-to-african-regional-languages-for-digital-inclusion/
50. https://research.google/blog/waxal-a-large-scale-open-resource-for-african-language-speech-technology/

### Articles scientifiques (arXiv non lisible : extraits)

51. https://arxiv.org/abs/2601.09716 (Mbaye et al., état du TAL pour les langues sénégalaises)
52. https://arxiv.org/abs/2509.15362 (Sy, Doucouré, Cerisara, Illina, LLM vocal wolof)
53. https://arxiv.org/abs/2610.20824 (Lecorvé et al., Orange, modèles wolof, 14/10/2026)
54. https://arxiv.org/abs/2602.02734 (WAXAL)
55. https://arxiv.org/abs/2404.01991 (Kallaama)

### Presse et réseaux sociaux (extraits)

56. https://aps.sn/intelligence-artificielle-15-equipes-selectionnees-pour-developper-des-solutions-vocales-en-langues-nationales/
57. https://fr.allafrica.com/stories/202610160715.html et https://fr.allafrica.com/stories/202610160690.html
58. https://www.rts.sn/actualite/detail/a-la-une/ia-et-langues-nationales-le-kiriku-voice-challenge-valorise-linnovation-numerique-au-senegal
59. https://www.terangatimesn.com/Intelligence-artificielle-et-inclusion-linguistique-Les-laureats-du-Kiriku-Voice-Challenge-recompenses-a-Dakar_a9643.html
60. https://lesoleil.sn/actualites/technologie/kiriku-voice-challenge-des-modeles-dia-developpes-pour-les-langues-nationales/
61. https://www.dakaractu.com/IA-et-langues-nationales-l-Etat-veut-transformer-les-prototypes-du-Kiriku-Challenge-en-services-durables_a277134.html
62. https://www.osiris.sn/ia-et-langues-nationales-l-etat-veut-transformer-les-prototypes-du-kiriku.html
63. https://houseof7international.substack.com/p/quinze-equipes-trois-langues-ce-que (analyse critique du challenge)
64. https://x.com/soynade/status/1868388486954504280 (15/12/2024, date tirée de l'identifiant du message)
65. https://x.com/Andakia_ai/status/1852509729655799929 (02/11/2024, date tirée de l'identifiant du message)
66. https://www.wearetech.africa/fr/fils/tech-stars/avec-l-ia-alioune-badara-mbengue-leve-les-barrieres-linguistiques-au-senegal
67. https://www.trtafrika.com/english/article/18244712
68. https://osiris.sn/awa-l-intelligence-artificielle-qui-parle-le-wolof-du-senegal.html
69. https://www.europe-infos.fr/actualites/11487/a-dakar-andakia-finalise-awa-ia-en-wolof-et-pulaar-au-telephone-et-sur-le-web-ce-que-la-start-up-doit-affronter/
70. https://theafricabusinessindex.com/2026/09/02/le-senegal-lance-awa-une-ia-capable-de-comprendre-le-wolof-et-le-pulaar/
71. https://forbesafrique.com/portrait-alioune-badara-mbengue/ et https://forbesafrique.com/produit/forbes-afrique-edition-de-mai-juin-2026-i-a-la-une-30-under-30-powerlist-2026-i-business-de-linfluence/
72. https://aps.sn/intelligence-artificielle-la-statistique-derriere-la-magie/
73. https://www.socialnetlink.org/2026/10/21/pas-challenge-2026-diagnostic-maturite-ia-senegal/
74. https://www.leral.net/Ndeye-Amy-Kebe-Jokalante-l-information-agricole-en-sept-langues_a408135.html
75. https://www.ietp.com/en/secteur-dactivit%C3%A9/digital-tech
76. https://www.wearetech.africa/fr/fils/solutions/senegal-sunu-souba-utilise-l-ia-pour-connecter-chercheurs-d-emploi-et-recruteurs et https://www.wearetech.africa/en/fils-uk/solutions/sunu-souba-leverages-ai-to-improve-hiring-efficiency-in-senegal
77. https://www.notrevoix.info/info/articles/sunu-souba-la-solution-senegalaise-qui-reinvente-l-acces-a-l-emploi-en-afrique-grace-a-l-intelligence-des-donnees
78. https://www.rts.sn/actualite/detail/a-la-une/smsi-2026-et-ai-for-good-le-senegal-brille-sur-la-scene-mondiale-de-linnovation-numerique-et-de-lintelligence-artificielle
79. https://www.ndarinfo.com/Deux-Champions-mondiaux-et-six-nominations-le-Senegal-dans-le-top-du-numerique-mondial-en-2026_a45568.html
80. https://www.pressafrik.com/Sommet-mondial-de-la-technologie-2026-le-Senegal-brille-avec-8-projets-retenus-et-des-distinctions-majeures-a-l-UIT_a308406.html
81. https://www.socialnetlink.org/2025/05/10/jangalma-le-champion-senegalais-du-e-learning-qui-revolutionne-leducation-avec-lia/
82. https://osiris.sn/jangalma-le-champion-senegalais-du-e-learning-qui-revolutionne-l-education-avec.html
83. https://apps.apple.com/sn/app/jangalma/id6477892059 et https://mwm.ai/apps/jangalma/6477892059
84. https://aps.sn/ai-karangue-une-innovation-senegalaise-basee-sur-lintelligence-artificielle-pour-reduire-les-accidents-routiers/
85. https://www.seneplus.com/article/ai-karangue-linnovation-senegalaise-qui-veut-prevenir-les-accidents-routiers
86. https://www.seneweb.com/en/news/Technologie/gitex-morocco-2026-senegal-on-top-of-africa-thanks-to-ai-karangue_n_489313.html
87. https://play.google.com/store/apps/details?id=sn.viepublique.app&hl=en_US
88. https://www.cnbc.com/2024/11/26/orange-partners-with-openai-meta-on-custom-african-language-ai-models.html
