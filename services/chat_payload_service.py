"""Chat payload construction and conversation-context preparation."""

import inspect
import logging
import re
import time

logger = logging.getLogger(__name__)

from .language_quality import language_instruction
from .intelligence import build_agent_plan, should_use_deep_reasoning
from .orchestrator import build_action_request, build_agent_plan as build_orchestrator_plan
from .action_executor import prepare_action


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

# Règles fixes : placées juste après le prompt système pour allonger le préfixe
# identique d'une requête à l'autre (mis en cache par OpenAI au-delà de 1024 tokens).
_KNOWLEDGE_WEB_RULE = (
    "COMBINAISON CONNAISSANCE + WEB : utilise la connaissance locale du Sénégal pour les faits stables, les repères géographiques et culturels et le contexte. "
    "Lorsque la recherche web est active, utilise ses résultats pour les informations susceptibles d’avoir changé et ne remplace pas silencieusement un fait local stable par une information web non vérifiée. "
    "Si les sources web contredisent la connaissance locale, privilégie la source la plus récente et fiable pour le fait dynamique, signale brièvement la différence si elle est utile, et ne transforme jamais une estimation locale en fait actuel."
)
_WEATHER_RULE = (
    "MÉTÉO : pour toute demande météo actuelle ou prévisionnelle, utilise la recherche web active et les résultats de la source autorisée. "
    "Pour le Sénégal, privilégie ANACIM. Donne la température ou les conditions réellement vérifiées, précise la période ou la date de validité et indique clairement la source. "
    "Si aucune donnée météo actuelle fiable n'est disponible, dis-le explicitement sans inventer et ne remplace pas ANACIM par une autre source non autorisée."
)
_FOLLOWUP_RULE = (
    "SUIVIS : si la demande est un suivi court, conserve le dernier référent pertinent. "
    "Si plusieurs référents sont réellement possibles, pose une seule question courte. "
    "Les éléments de la section CONTEXTE DE LA DEMANDE sont des déductions automatiques : ne les cite pas comme si l'utilisateur les avait explicitement déclarés."
)
STATIC_RULES = "\n\n".join((_KNOWLEDGE_WEB_RULE, _WEATHER_RULE, _FOLLOWUP_RULE))

_STEP_LABELS = {
    "prepare_context": "préparer le contexte",
    "web_retrieval": "recherche web",
    "build_plan": "construire un plan",
    "prepare_action": "préparer une action (confirmation requise)",
    "generate_response": "répondre",
    "image_enrichment": "photos ajoutées par l'interface",
    "map_enrichment": "carte ajoutée par l'interface",
    "finalize": "finaliser",
}


def _format_plan(plan, *, planner: bool, use_web: bool) -> str:
    """Readable execution plan for the model (no internal model names).

    ``planner`` and ``use_web`` are the request's final decisions, so the text
    never contradicts what the model is actually given (tools, plan mode).
    """
    steps = [step for step in (getattr(plan, "steps", ()) or ()) if step != "web_retrieval" or use_web]
    if use_web and "web_retrieval" not in steps:
        steps.insert(1 if steps else 0, "web_retrieval")
    if planner and "build_plan" not in steps:
        anchor = steps.index("generate_response") if "generate_response" in steps else len(steps)
        steps.insert(anchor, "build_plan")
    labels = " → ".join(_STEP_LABELS.get(step, step) for step in steps) or "répondre"
    parts = [f"étapes : {labels}", "recherche web : " + ("oui" if use_web else "non")]
    parts.append("sources : connaissance locale + web" if use_web else "sources : connaissance locale")
    return "PLAN D’EXÉCUTION : " + " ; ".join(parts) + "."


_MEMORY_LABELS = {
    "place": "lieu",
    "budget": "budget",
    "duration": "durée",
    "adults": "adultes",
    "children": "enfants",
    "constraints": "contraintes",
    "family": "famille",
}


_CONSTRAINT_PREFIXES_COVERED = {
    "budget": "budget=",
    "duration": "durée=",
    "adults": "adultes=",
    "children": "enfants=",
    "family": "famille",
}


def _format_memory(memory) -> str:
    """Render the structured memory once, without duplicated keys."""
    if not isinstance(memory, dict) or not memory:
        return "aucune"
    temporary = memory.get("temporary")
    if not isinstance(temporary, dict):
        temporary = {k: v for k, v in memory.items() if k in _MEMORY_LABELS}
    parts = []
    for key in ("place", "budget", "duration", "adults", "children", "family"):
        value = temporary.get(key)
        if value in (None, "", [], False):
            continue
        parts.append(f"{_MEMORY_LABELS[key]} = {'oui' if value is True else value}")
    covered = tuple(prefix for key, prefix in _CONSTRAINT_PREFIXES_COVERED.items() if temporary.get(key) not in (None, "", [], False))
    others = [str(c) for c in (temporary.get("constraints") or []) if not str(c).startswith(covered)]
    if others:
        parts.append("autres contraintes = " + ", ".join(others))
    preferences = [str(p) for p in (memory.get("durable_candidates") or []) if p]
    if preferences:
        parts.append("préférences exprimées = " + " / ".join(preferences))
    return " ; ".join(parts) or "aucune"


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

    action_confirmed = data.get("action_confirmed") is True
    action_request_id = str(data.get("action_request_id") or "").strip()
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
    agent_plan = build_orchestrator_plan({**context, "action_confirmed": action_confirmed, "use_web": bool(intent_context.get("needs_web_search")), "message": message, "intent_context": intent_context}, model="gpt-5.6-luna")
    memory_line = (
        "MÉMOIRE STRUCTURÉE COURTE : "
        + _format_memory(structured_memory)
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
    photo_only = (
        bool(re.search(r"\bphotos?\b|\bimages?\b", message.lower()))
        or (intent_context.get("intent") == "photos" and set(context.get("intents", [])) <= {"photos"})
    )
    use_web = False if photo_only else bool(intent_context.get("needs_web_search"))
    context_instruction = " ".join(
        part for part in (
            place_line,
            trip_context_line,
            trip_edit_line,
            intent_line,
            constraint_line,
            planner_line,
            "Domaine Sénégal détecté : " + str(intent_context.get("domain") or "general") + ".",
            _format_plan(agent_plan, planner=planner_enabled, use_web=use_web),
            memory_line,
            source_line,
            planner_instruction,
        )
        if part
    )
    audience_instruction = _AUDIENCE_INSTRUCTIONS[audience][language]
    started_at = time.perf_counter()
    knowledge_context = format_senegal_knowledge(senegal_knowledge, query=enriched_context, people=senegal_people)
    logger.info("chat_knowledge_format_ms %.2f", (time.perf_counter() - started_at) * 1000)
    started_at = time.perf_counter()
    conversation_input = build_conversation(history, message, max_history_items=max_history_items, max_history_item_length=max_history_item_length, max_history_chars=max_history_chars)
    logger.info("chat_conversation_build_ms %.2f", (time.perf_counter() - started_at) * 1000)
    return {
        # Ordre : du plus stable au plus variable, pour maximiser le cache de prompt.
        "instructions": "\n\n".join(
            part for part in (
                system_prompt.strip(),
                STATIC_RULES,
                language_instruction_text,
                audience_instruction,
                knowledge_context,
                "CONTEXTE DE LA DEMANDE :\n" + context_instruction,
            )
            if part
        ),
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
        "action_request": ({**build_action_request({**context, "action_confirmed": action_confirmed, "action_request_id": action_request_id}, agent_plan), **({"request_id": prepare_action(agent_plan.action).request_id} if agent_plan.action != "answer" and not action_confirmed else {})}),
        "ux_hints": intent_context.get("ux_hints") or {"mode": "answer", "followups": [], "show_followups": False, "compact": True},
        "contextual_query": enriched_context,
        "trip_context": trip_context,
        "trip_edit_request": trip_edit_request,
        "trip_edit_proposal": trip_edit_proposal,
    }, None
