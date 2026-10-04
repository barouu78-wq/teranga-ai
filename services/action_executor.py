"""Bounded execution contract for Teranga AI actions.

This module deliberately does not perform network or external side effects.
It validates and dispatches only allowlisted internal action handlers supplied
by the caller, and requires explicit confirmation for execution.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


ALLOWED_ACTIONS = frozenset(
    {
        "prepare_trip_plan",
        "prepare_route",
        "prepare_restaurant_options",
        "prepare_project_plan",
        "prepare_career_plan",
        "prepare_learning_plan",
        "prepare_finance_plan",
    }
)


@dataclass(frozen=True)
class ActionExecutionResult:
    action: str
    status: str
    executed: bool
    requires_confirmation: bool
    result: Any = None


def execute_action(
    action: str,
    *,
    confirmed: bool = False,
    handlers: dict[str, Callable[[], Any]] | None = None,
) -> ActionExecutionResult:
    """Execute only an allowlisted handler after explicit confirmation."""
    if action not in ALLOWED_ACTIONS:
        return ActionExecutionResult(
            action=action,
            status="unsupported",
            executed=False,
            requires_confirmation=False,
        )

    if not confirmed:
        return ActionExecutionResult(
            action=action,
            status="confirmation_required",
            executed=False,
            requires_confirmation=True,
        )

    handler = (handlers or {}).get(action)
    if handler is None:
        return ActionExecutionResult(
            action=action,
            status="not_implemented",
            executed=False,
            requires_confirmation=False,
        )

    return ActionExecutionResult(
        action=action,
        status="executed",
        executed=True,
        requires_confirmation=False,
        result=handler(),
    )
