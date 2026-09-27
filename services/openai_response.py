"""Provider response orchestration helpers for Teranga AI."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


def create_response(
    client: Any,
    payload: dict[str, Any],
    *,
    build_kwargs: Callable[[dict[str, Any], bool], dict[str, Any]],
    model: str,
    logger: Any,
    stream: bool,
    fallback_models: tuple[str, ...] = (),
):
    kwargs = build_kwargs(payload, stream)
    try:
        return client.responses.create(**kwargs)
    except Exception as exc:
        text = f"{type(exc).__name__} {exc}".lower()
        model_error = "model" in text and any(
            marker in text
            for marker in (
                "not found",
                "does not exist",
                "not available",
                "unsupported",
                "not permitted",
            )
        )
        if not model_error:
            raise
        for fallback_model in fallback_models:
            if fallback_model == model:
                continue
            fallback = dict(kwargs)
            fallback["model"] = fallback_model
            logger.warning("Modèle %s indisponible; tentative avec %s", model, fallback_model)
            return client.responses.create(**fallback)
        raise
