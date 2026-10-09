"""Bounded agent orchestration for Teranga AI.

Planning is deterministic and bounded. Tool enrichment is explicitly selected
by request intent and each optional tool is isolated from the others.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any, Callable
from concurrent.futures import ThreadPoolExecutor

from .action_executor import ALLOWED_ACTIONS
from .model_params import openai_complex_model, openai_model


@dataclass(frozen=True)
class AgentPlan:
    """Immutable execution plan for one chat request."""

    model: str
    use_web: bool = False
    use_images: bool = False
    use_map: bool = False
    planner: bool = False
    workflow: str = "general"
    deep_reasoning: bool = False
    steps: tuple[str, ...] = field(default_factory=tuple)
    source_strategy: str = "local"
    action_strategy: str = "answer"
    action: str = "answer"
    execution_mode: str = "answer"
    requires_confirmation: bool = False


def _contains_query_term(query: str, term: str) -> bool:
    """Match a map hint as a complete word or phrase, not a substring."""
    pattern = r"(?<!\w)" + re.escape(term) + r"(?!\w)"
    return bool(re.search(pattern, query))


def _needs_map(payload: dict[str, Any]) -> bool:
    """Select maps only for location/route-oriented requests."""
    intent_context = payload.get("intent_context") or {}
    intent = str(intent_context.get("intent") or "")
    if intent in {"trip_planning", "transport"}:
        return True
    if intent_context.get("location") and intent in {"photos", "general_information", "culture"}:
        query = str(payload.get("message") or "").lower()
        return any(
            _contains_query_term(query, term)
            for term in ("où", "ou", "carte", "localiser", "situe", "situé", "route")
        )
    return False


_PLANNER_WORKFLOW_ALIASES = {
    "trip_planning": "travel",
    "travel": "travel",
    "project": "project",
    "career": "career",
    "education": "education",
    "finance": "finance",
}


def build_action_request(payload: dict[str, Any], plan: AgentPlan) -> dict[str, Any]:
    """Create a bounded action contract; external side effects always require confirmation."""
    if plan.action == "answer":
        return {"enabled": False, "action": "answer", "execution_mode": "answer", "requires_confirmation": False}
    confirmed = bool(payload.get("action_confirmed"))
    request_id = str(payload.get("action_request_id") or "").strip()
    if plan.action not in ALLOWED_ACTIONS:
        return {"enabled": False, "action": plan.action, "execution_mode": "unsupported", "requires_confirmation": False}
    execution_mode = "execute" if confirmed and request_id else "prepare"
    return {
        "enabled": True,
        "action": plan.action,
        "execution_mode": execution_mode,
        "requires_confirmation": execution_mode != "execute",
        "confirmed": execution_mode == "execute",
        "request_id": request_id,
    }


def build_agent_plan(payload: dict[str, Any], *, model: str, complex_model: str | None = None) -> AgentPlan:
    """Build a bounded plan from the decisions already computed upstream.

    ``complex_model`` absent : modèle configuré par OPENAI_COMPLEX_MODEL. Une chaîne vide
    désactive le passage au modèle complexe. Seul le modèle rapide (OPENAI_MODEL) y passe.
    """
    if complex_model is None:
        complex_model = openai_complex_model()
    planner = bool(payload.get("planner"))
    deep_reasoning = bool(payload.get("deep_reasoning"))
    use_web = bool(payload.get("use_web"))
    intent_context = payload.get("intent_context") or {}
    use_images = bool(intent_context.get("needs_images")) and not planner
    use_map = _needs_map(payload)
    has_local_context = bool(payload.get("senegal_knowledge") or intent_context.get("location") or intent_context.get("has_context"))
    if use_web and has_local_context:
        source_strategy = "hybrid"
    elif use_web:
        source_strategy = "web"
    else:
        source_strategy = "local"
    action_intents = {"trip_planning", "transport", "restaurant", "project", "career", "education", "finance"}
    requested_workflow = str(intent_context.get("intent") or "").strip().lower()
    action_strategy = "act" if requested_workflow in action_intents and (planner or use_map or use_web) else "answer"
    action = {
        "trip_planning": "prepare_trip_plan",
        "transport": "prepare_route",
        "restaurant": "prepare_restaurant_options",
        "project": "prepare_project_plan",
        "career": "prepare_career_plan",
        "education": "prepare_learning_plan",
        "finance": "prepare_finance_plan",
    }.get(requested_workflow, "answer") if action_strategy == "act" else "answer"
    workflow = _PLANNER_WORKFLOW_ALIASES.get(requested_workflow, "general") if planner else "general"
    active_model = complex_model if model == openai_model() and complex_model and (planner or deep_reasoning) else model
    steps = ["prepare_context"]
    if use_web:
        steps.append("web_retrieval")
    if planner:
        steps.append("build_plan")
    if action_strategy == "act":
        steps.append("prepare_action")
    steps.append("generate_response")
    if use_images:
        steps.append("image_enrichment")
    if use_map:
        steps.append("map_enrichment")
    steps.append("finalize")
    return AgentPlan(
        model=active_model,
        use_web=use_web,
        use_images=use_images,
        use_map=use_map,
        planner=planner,
        workflow=workflow,
        deep_reasoning=deep_reasoning,
        steps=tuple(steps),
        source_strategy=source_strategy,
        action_strategy=action_strategy,
        action=action,
        execution_mode="prepare" if action != "answer" else "answer",
        requires_confirmation=action != "answer" and not (bool(payload.get("action_confirmed")) and bool(payload.get("action_request_id"))),
    )



def run_enrichments(
    plan: AgentPlan,
    *,
    message: str,
    contextual_query: str,
    fetch_images: Callable[[str], Any],
    lookup_map: Callable[[str, bool], Any],
    should_fetch_map: Callable[[str], bool],
    logger: Any = None,
) -> tuple[Any, Any]:
    """Run selected enrichments independently, in parallel when both are selected."""
    def fetch_image_result():
        try:
            return fetch_images(message)
        except Exception:
            if logger is not None and hasattr(logger, "exception"):
                logger.exception("agent_image_enrichment_failed")
            return None

    def fetch_map_result():
        try:
            query = contextual_query or message
            return lookup_map(query, should_fetch_map(query))
        except Exception:
            if logger is not None and hasattr(logger, "exception"):
                logger.exception("agent_map_enrichment_failed")
            return None

    if plan.use_images and plan.use_map:
        with ThreadPoolExecutor(max_workers=2, thread_name_prefix="chat-enrichment") as executor:
            image_future = executor.submit(fetch_image_result)
            map_future = executor.submit(fetch_map_result)
            return image_future.result(), map_future.result()
    if plan.use_images:
        return fetch_image_result(), None
    if plan.use_map:
        return None, fetch_map_result()
    return None, None
