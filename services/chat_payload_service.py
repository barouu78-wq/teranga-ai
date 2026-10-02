"""Chat payload construction and conversation-context preparation."""

import inspect
import logging
import re
import time

logger = logging.getLogger(__name__)

from .language_quality import language_instruction
from .intelligence import build_agent_plan, should_use_deep_reasoning


_AUDIENCE_INSTRUCTIONS = {
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
}

_REGION_NAMES = {name.casefold(): name for name in ("Dakar","Diourbel","Fatick","Kaffrine","Kaolack","Kédougou","Kolda","Louga","Matam","Saint-Louis","Sédhiou","Tambacounda","Thiès","Ziguinchor")}


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
        return None, "invalid"
    if error == "empty":
        return None, "empty"

    message = normalized["message"]
    history = normalized["history"]
    language = normalized["language"]
    audience = normalized["audience"]
    language_instruction_text = language_instruction(language)
    started_at = time.perf_counter()
    context = infer_senegal_context(history, message)
    logger.info("chat_context_infer_ms %.2f", (time.perf_counter() - started_at) * 1000)
    selected_place = normalized.get("context_place", "")
    trip_context = normalized.get("trip_context", "")
    trip_edit_request = normalized.get("trip_edit_request", "")
    selected_place_from_ui = bool(selected_place and not context.get("has_place"))
    if selected_place_from_ui:
        context["has_place"] = True
        context["place"] = selected_place
        context["query"] = f"{selected_place} : {message}"
    started_at = time.perf_counter()
    if "resolved_context" in inspect.signature(build_intent_context).parameters:
        intent_context = build_intent_context(message, history, resolved_context=context)
    else:
        intent_context = build_intent_context(message, history)
    logger.info("chat_intent_context_ms %.2f", (time.perf_counter() - started_at) * 1000)
    trip_edit_line = ""
    if trip_edit_request:
        trip_edit_line = ("Demande explicite de modification d’itinéraire fournie par l’interface : " + trip_edit_request + ". " "Ne l’applique jamais automatiquement ; prépare uniquement une proposition structurée si la demande est suffisamment précise.")
    trip_context_line = ""
    if trip_context:
        trip_context_line = (
            "Contexte d’itinéraire fourni par l’interface (modifiable par l’utilisateur) : "
            f"{trip_context}"
        )
    enriched_context = context["query"]
    if context["has_place"]:
        if selected_place_from_ui:
            place_line = (
                f"Repère fourni par l’interface : {context['place']}. "
                "Utilise ce lieu pour le suivi demandé, sans le présenter comme une localisation certaine de l’utilisateur."
            )
        else:
            place_line = (
                f"Contexte géographique détecté : {context['place']}. "
                "Utilise ce repère pour les suivis courts, sans transformer une déduction en certitude."
            )
    else:
        place_line = "Aucun lieu sénégalais fiable n'a été détecté ; n'invente pas de localisation."
    intent_line = "Intentions détectées : " + (", ".join(context.get("intents", [])) or "générale") + "."
    constraint_line = "Contraintes détectées : " + (", ".join(context.get("constraints", [])) or "aucune") + "."
    structured_memory = intent_context.get("memory") or {}
    agent_plan = build_agent_plan(context, intent_context)
    memory_line = (
        "MÉMOIRE STRUCTURÉE COURTE : "
        + str(structured_memory)
        + ". Utilise-la uniquement pour conserver les contraintes utiles du fil récent ; ne la traite jamais comme un profil permanent."
    )
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
    trip_edit_proposal = None
    region_names = _REGION_NAMES
    edit_match = re.search(
        r"\b(?:remplace|change|modifier|modifie|replace|edit)\s+(?:le\s+)?(?:jour|day)\s*(\d+)\s+(?:par|avec|to)\s+",
        trip_edit_request,
        re.I,
    )
    if edit_match and trip_context:
        day = int(edit_match.group(1))
        if 1 <= day <= 14:
            remainder = trip_edit_request[edit_match.end():]
            region = next(
                (canonical for key, canonical in region_names.items() if re.match(rf"{re.escape(key)}(?:\b|\s|$)", remainder.strip().casefold())),
                None,
            )
            if region:
                trip_edit_proposal = {"action": "replace_day_region", "day": day, "region": region, "requires_confirmation": True}
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
    knowledge_web_line = (
        "COMBINAISON CONNAISSANCE + WEB : utilise la connaissance locale du Sénégal pour les faits stables, les repères géographiques et culturels et le contexte. "
        "Lorsque la recherche web est active, utilise ses résultats pour les informations susceptibles d’avoir changé et ne remplace pas silencieusement un fait local stable par une information web non vérifiée. "
        "Si les sources web contredisent la connaissance locale, privilégie la source la plus récente et fiable pour le fait dynamique, signale brièvement la différence si elle est utile, et ne transforme jamais une estimation locale en fait actuel."
    )
    context_instruction = (
        place_line + " " + trip_context_line + " " + trip_edit_line + " " + intent_line + " " + constraint_line + " " + planner_line + " " +
        "Domaine Sénégal détecté : " + str(intent_context.get("domain") or "general") + ". " +
        "PLAN D’EXÉCUTION : " + str(agent_plan) + ". " +
        memory_line + " " +
        knowledge_web_line + " " + source_line + " " + planner_instruction +
        " Si la demande est un suivi court, conserve le dernier référent pertinent. " +
        "Si plusieurs référents sont réellement possibles, pose une seule question courte. " +
        "Ne cite pas ces déductions comme si l'utilisateur les avait explicitement déclarées."
    )
    audience_instruction = _AUDIENCE_INSTRUCTIONS[audience][language]
    photo_only = (
        bool(re.search(r"\bphotos?\b|\bimages?\b", message.lower()))
        or (intent_context.get("intent") == "photos" and set(context.get("intents", [])) <= {"photos"})
    )
    use_web = False if photo_only else bool(intent_context.get("needs_web_search"))
    started_at = time.perf_counter()
    knowledge_context = format_senegal_knowledge(senegal_knowledge, query=enriched_context, people=senegal_people)
    logger.info("chat_knowledge_format_ms %.2f", (time.perf_counter() - started_at) * 1000)
    started_at = time.perf_counter()
    conversation_input = build_conversation(history, message, max_history_items=max_history_items, max_history_item_length=max_history_item_length, max_history_chars=max_history_chars)
    logger.info("chat_conversation_build_ms %.2f", (time.perf_counter() - started_at) * 1000)
    return {
        "instructions": system_prompt + "\\n" + knowledge_context + "\\n" + language_instruction_text + "\\n" + audience_instruction + "\\n" + context_instruction,
        "input_text": conversation_input,
        "use_web": use_web,
        "planner": planner_enabled,
        "deep_reasoning": bool(intent_context.get("needs_deep_reasoning")),
        "planner_data": planner_data,
        "message": message,
        "audience": audience,
        "context": context,
        "intent_context": intent_context,
        "memory": structured_memory,
        "agent_plan": agent_plan,
        "contextual_query": enriched_context,
        "trip_context": trip_context,
        "trip_edit_request": trip_edit_request,
        "trip_edit_proposal": trip_edit_proposal,
    }, None
