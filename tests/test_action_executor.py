from services.action_executor import ALLOWED_ACTIONS, execute_action


def test_unsupported_action_is_rejected():
    result = execute_action("delete_user", confirmed=True)
    assert result.status == "unsupported"
    assert result.executed is False


def test_supported_action_requires_confirmation():
    result = execute_action("prepare_trip_plan")
    assert result.status == "confirmation_required"
    assert result.requires_confirmation is True
    assert result.executed is False


def test_confirmed_action_executes_only_supplied_handler():
    called = []
    result = execute_action(
        "prepare_trip_plan",
        confirmed=True,
        handlers={"prepare_trip_plan": lambda: called.append("ok") or {"ready": True}},
    )
    assert result.status == "executed"
    assert result.executed is True
    assert result.result == {"ready": True}
    assert called == ["ok"]


def test_allowlist_is_explicit():
    assert "prepare_trip_plan" in ALLOWED_ACTIONS
    assert "delete_user" not in ALLOWED_ACTIONS
