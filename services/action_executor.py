"""Bounded execution contract for Teranga AI actions.

This module deliberately does not perform network or external side effects.
It validates and dispatches only allowlisted internal action handlers supplied
by the caller, and requires explicit confirmation for execution.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable
from uuid import uuid4


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
    request_id: str = ""


def prepare_action(action: str) -> ActionExecutionResult:
    """Create an idempotent-looking action request without executing it."""
    request_id = uuid4().hex
    if action not in ALLOWED_ACTIONS:
        return ActionExecutionResult(action=action, status="unsupported", executed=False, requires_confirmation=False, request_id=request_id)
    return ActionExecutionResult(action=action, status="prepared", executed=False, requires_confirmation=True, request_id=request_id)


def execute_action(
    action: str,
    *,
    confirmed: bool = False,
    handlers: dict[str, Callable[[], Any]] | None = None,
) -> ActionExecutionResult:
    """Execute only an allowlisted handler after explicit confirmation."""
    request_id = uuid4().hex
    if action not in ALLOWED_ACTIONS:
        return ActionExecutionResult(
            action=action,
            status="unsupported",
            executed=False,
            requires_confirmation=False,
            request_id=request_id,
        )

    if not confirmed:
        return ActionExecutionResult(
            action=action,
            status="confirmation_required",
            executed=False,
            requires_confirmation=True,
            request_id=request_id,
        )

    handler = (handlers or {}).get(action)
    if handler is None:
        return ActionExecutionResult(
            action=action,
            status="not_implemented",
            executed=False,
            requires_confirmation=False,
            request_id=request_id,
        )

    return ActionExecutionResult(
        action=action,
        status="executed",
        executed=True,
        requires_confirmation=False,
        result=handler(),
        request_id=request_id,
    )
