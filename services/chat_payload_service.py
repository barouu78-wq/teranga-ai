"""Chat payload construction and conversation-context preparation."""

from flask import jsonify


def build_chat_payload(data, *, sanitize, normalize_chat_input, max_message_length, max_history_items, max_history_item_length, safe_languages, infer_senegal_context, build_intent_context, should_use_planner, build_planner_data, should_use_web, format_senegal_knowledge, senegal_knowledge, senegal_people, build_conversation, max_history_chars, system_prompt):
    normalized, error = normalize_chat_input(
        data,
        sanitize=sanitize,
        max_message_length=max_message_length,
        max_history_items=max_history_items,
        max_history_item_length=max_history_item_length,
        safe_languages=safe_languages,
    )
    if error == "invalid":
        return None, (jsonify({"error": "Requête invalide."}), 400)
    if error == "empty":
        return None, (jsonify({"error": "Écris un message avant d'envoyer."}), 400)

    message = normalized["message"]
    history = normalized["history"]
    language = normalized["language"]
    audience = normalized["audience"]
    language_instruction = {
        "fr": "Réponds en français naturel, avec un vocabulaire sénégalais naturel quand le contexte s'y prête.",
        "en": "Reply in natural English. Keep Senegalese names, places, dishes and cultural terms in their established form.",
        "wo": "Réponds en wolof naturel autant que possible. Garde les noms propres, lieux et plats dans leur forme usuelle. N'abandonne pas le wolof pour le français simplement parce qu'une phrase est un peu plus difficile ; utilise le français seulement pour un terme technique ou un mot réellement intraduisible, puis continue en wolof. Si l'utilisateur mélange wolof et français, comprends le mélange et réponds majoritairement en wolof.",
        "ff": "Réponds en pulaar naturel (fuuta tooro) autant que possible. Garde les noms propres, lieux et plats dans leur forme usuelle. N'abandonne pas le pulaar pour le français simplement parce qu'une phrase est un peu plus difficile ; utilise le français seulement pour un terme technique ou un mot réellement intraduisible, puis continue en pulaar. Si l'utilisateur mélange pulaar et français, comprends le mélange et réponds majoritairement en pulaar. Respecte l'orthographe pulaar fournie par l'utilisateur quand elle est claire.",
    }[language]
    context = infer_senegal_context(history, message)
    intent_context = build_intent_context(message, history)
    enriched_context = context["query"]
    if context["has_place"]:
        place_line = (
            f"Contexte géographique détecté : {context['place']}. "
            "Utilise ce repère pour les suivis courts, sans transformer une déduction en certitude."
        )
    else:
        place_line = "Aucun lieu sénégalais fiable n'a été détecté ; n'invente pas de localisation."
    intent_line = "Intentions détectées : " + (", ".join(context.get("intents", [])) or "générale") + "."
    constraint_line = "Contraintes détectées : " + (", ".join(context.get("constraints", [])) or "aucune") + "."
    planner_enabled = should_use_planner(context)
    planner_data = build_planner_data(context) if planner_enabled else {}
    planner_line = "Mode planification recommandé : oui." if planner_enabled else "Mode planification recommandé : non."
    if planner_enabled:
        planner_instruction = (
            "MODE PLANIFICATION ACTIF : transforme la demande en plan concret et directement exploitable. "
            "Utilise d'abord les contraintes détectées (lieu, durée, budget, famille/enfants, moment) et les éléments explicitement demandés. "
            "Si une information essentielle manque, fais une hypothèse raisonnable et indique-la brièvement au lieu de bloquer la réponse. "
            "Organise le plan dans un ordre logique et chronologique. Pour un séjour ou une journée, propose des étapes par jour ou par période, avec déplacement, activité et repas lorsque pertinent. "
            "Si un budget est fourni, répartis-le en postes utiles et donne un total indicatif ; ne présente jamais une estimation comme un prix vérifié. "
            "Pour les horaires, prix, disponibilités, transports, météo ou événements susceptibles de changer, utilise la recherche web si disponible et distingue clairement ce qui est vérifié de ce qui reste indicatif. "
            "Évite les détours et les listes interminables : privilégie un plan réaliste, avec une alternative simple si une étape peut être indisponible."
        )
    else:
        planner_instruction = ""
    preferred = tuple(intent_context.get("preferred_sources") or ())
    if preferred:
        source_line = (
            "POLITIQUE DE SOURCES : pour la recherche web, privilégie ces domaines de référence : "
            + ", ".join(preferred) + ". "
            "Pour les faits actuels, cite uniquement les éléments réellement vérifiés par les résultats disponibles."
        )
    else:
        source_line = (
            "POLITIQUE DE SOURCES : privilégie les sources institutionnelles ou spécialisées fiables "
            "et vérifie les faits actuels avant de les présenter comme actuels."
        )
    context_instruction = (
        place_line + " " + intent_line + " " + constraint_line + " " + planner_line + " " +
        "Domaine Sénégal détecté : " + str(intent_context.get("domain") or "general") + ". " +
        source_line + " " + planner_instruction +
        " Si la demande est un suivi court, conserve le dernier référent pertinent. " +
        "Si plusieurs référents sont réellement possibles, pose une seule question courte. " +
        "Ne cite pas ces déductions comme si l'utilisateur les avait explicitement déclarées."
    )
    audience_instruction = {
        "tourist": {
            "fr": "Profil actif : touriste. Oriente prioritairement vers des réponses pratiques pour voyager : déplacements, budget indicatif, horaires à vérifier, sécurité pratique, culture, nourriture, langues utiles et expériences. Signale les informations qui changent et propose des étapes concrètes.",
            "en": "Active profile: tourist. Prioritize practical travel help: transport, indicative budgets, schedules to verify, practical safety, culture, food, useful languages and experiences. Flag changing information and give concrete next steps.",
            "wo": "Profil bi mooy tukki. Jox ndimbal bu jëm ci yoon, budget, waxtu yu wara ñu seet, aar, aada, ñam ak wax yu am solo. Wax lu mëna soppi, te jox jéego yu leer.",
            "ff": "Profil ngol yahduɗo. Hokkude ballal e laawol, budget, waqtuji, kisal, aada, ñaamdu e konngi nafata. Hollu ko waawi waylude, tee hokku peeje ɗeŋngal."
        },
        "resident": {
            "fr": "Profil actif : résident. Priorise la vie quotidienne au Sénégal : démarches, logement, budget, paiements, transport, services locaux, santé pratique et organisation du quotidien. Vérifie les règles, tarifs et horaires actuels quand ils changent.",
            "en": "Active profile: resident. Prioritize everyday life in Senegal: paperwork, housing, budgeting, payments, transport, local services, practical health and daily organization. Verify changing rules, fees and schedules.",
            "wo": "Profil bi mooy dundkat. Jox ndimbal ci dund bés bu nekk: formalité, kër, budget, fey, yoon, services, aar ak doxalin. Seet lu bees bu ko soxla.",
            "ff": "Profil ngol dunndotoowo. Hokkude ballal e dund bés e Senegaal: formalité, suudu, budget, feyde, laawol, sarwiis e doxalin. Ƴeewto ko hesɗi so ina waɗi."
        },
        "diaspora": {
            "fr": "Profil actif : diaspora. Priorise la préparation de séjours et retours au Sénégal, la gestion à distance, les transferts d'argent, les dépenses familiales, le logement, les projets et investissements. Sépare clairement les informations indicatives des règles ou tarifs à vérifier.",
            "en": "Active profile: diaspora. Prioritize planning stays and returns to Senegal, remote management, money transfers, family expenses, housing, projects and investments. Clearly separate indicative information from rules or fees that must be verified.",
            "wo": "Profil bi mooy diaspora. Jox ndimbal ci waajal tukki walla dellusi, doxal ci sore, yónnee xaalis, dépense famille, kër, projet ak investissement. Seet lu bees te wone ko bu leer.",
            "ff": "Profil ngol diaspora. Hokkude ballal e waajta yahdugol walla ruttorde, doxal daga woɗnde, yónnude ceede, dépense ɓeyngu, suudu, projet e investissement. Ƴeewto ko hesɗi tee hollu ko misaal tan."
        },
        "merchant": {
            "fr": "Profil actif : commerçant. Oriente prioritairement vers des réponses utiles à une petite activité au Sénégal : prix et marge, offre, clientèle, vente en ligne, WhatsApp, paiements, stock, livraison, formalités et accueil des touristes. Donne des méthodes simples, des exemples chiffrés clairement présentés comme indicatifs et vérifie les règles ou tarifs actuels si nécessaire.",
            "en": "Active profile: merchant. Prioritize practical help for a small business in Senegal: pricing and margins, offers, customers, online sales, WhatsApp, payments, stock, delivery, formalities and serving tourists. Give simple methods, clearly label example figures as indicative, and verify current rules or fees when needed.",
            "wo": "Profil bi mooy jaaykat. Jox ndimbal bu jëm ci njëg ak marge, clients, jaay online, WhatsApp, fey, stock, livraison, formalités ak accueil turist yi. Jëfandikoo yoon yu yomb, te bu amee xaalis wax ne misaal la; seet lu bees bu ko soxla.",
            "ff": "Profil ngol jaaytoowo. Hokkude ballal e ndeeƴre e marge, clients, jaaygol online, WhatsApp, feyde, stock, yahrude e formalités, e jaɓɓugol yahduɓe. Huutoro laawol hoyre, hollu misaaliji ceede ko misaal tan, tee ƴeewto ko hesɗi so ina waɗi."
        }
    }[audience][language]
    return {
        "instructions": system_prompt + "\\n" + format_senegal_knowledge(SENEGAL_KNOWLEDGE, query=enriched_context, people=SENEGAL_PEOPLE) + "
" + language_instruction + "
" + audience_instruction + "
" + context_instruction,
        "input_text": build_conversation(history, message, max_history_items=max_history_items, max_history_item_length=max_history_item_length, max_history_chars=max_history_chars),
        "use_web": should_use_web(message, enriched_context),
        "planner": planner_enabled,
        "planner_data": planner_data,
        "message": message,
        "audience": audience,
        "context": context,
        "intent_context": intent_context,
        "contextual_query": enriched_context,
    }, None
