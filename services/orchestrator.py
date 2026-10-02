"""Bounded agent orchestration for Teranga AI.

This module turns an already-resolved chat payload into one deterministic
execution plan. It deliberately does not implement an autonomous loop:
planning, model selection, and enrichment remain bounded and observable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass(frozen=True)
class AgentPlan:
    """Immutable execution plan for one chat request."""

    model: str
    use_web: bool = False
    use_images: bool = False
    use_map: bool = False
    planner: bool = False
    deep_reasoning: bool = False
    steps: tuple[str, ...] = field(default_factory=tuple)


def build_agent_plan(
    payload: dict[str, Any],
    *,
    model: str,
    complex_model: str = "gpt-5.6-sol",
) -> AgentPlan:
    """Build a bounded plan from the decisions already computed upstream."""
    planner = bool(payload.get("planner"))
    deep_reasoning = bool(payload.get("deep_reasoning"))
    use_web = bool(payload.get("use_web"))
    intent_context = payload.get("intent_context") or {}

    use_images = bool(intent_context.get("needs_images")) and not planner
    use_map = bool(payload.get("contextual_query") or payload.get("message"))

    active_model = (
        complex_model
        if model == "gpt-5.6-luna" and complex_model and (planner or deep_reasoning)
        else model
    )

    steps = ["prepare_context"]
    if use_web:
        steps.append("web_retrieval")
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
        deep_reasoning=deep_reasoning,
        steps=tuple(steps),
    )


def run_enrichments(
    plan: AgentPlan,
    *,
    message: str,
    contextual_query: str,
    fetch_images: Callable[[str], Any],
    lookup_map: Callable[[str, bool], Any],
    should_fetch_map: Callable[[str], bool],
) -> tuple[Any, Any]:
    """Run only the bounded enrichments selected by the plan."""
    image = None
    map_result = None
    if plan.use_images:
        image = fetch_images(message)
    if plan.use_map:
        map_result = lookup_map(
            contextual_query or message,
            should_fetch_map(contextual_query or message),
        )
    return image, map_result
