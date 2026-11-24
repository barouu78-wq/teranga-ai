"""Bounded execution contract for Teranga AI actions.

This module deliberately does not perform network or external side effects.
It validates and dispatches only allowlisted internal action handlers supplied
by the caller, and requires explicit confirmation for execution.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
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
    """Create a fresh preparation request without executing anything."""
    request_id = uuid4().hex
    if action not in ALLOWED_ACTIONS:
        return ActionExecutionResult(
            action=action,
            status="unsupported",
            executed=False,
            requires_confirmation=False,
            request_id=request_id,
        )
    return ActionExecutionResult(
        action=action,
        status="prepared",
        executed=False,
        requires_confirmation=True,
        request_id=request_id,
    )
