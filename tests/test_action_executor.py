from services.action_executor import ALLOWED_ACTIONS, execute_action, prepare_action


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



def test_prepare_action_creates_request_without_execution():
    result = prepare_action("prepare_trip_plan")
    assert result.status == "prepared"
    assert result.executed is False
    assert result.requires_confirmation is True
    assert result.request_id


def test_prepare_unsupported_action_is_safe():
    result = prepare_action("delete_user")
    assert result.status == "unsupported"
    assert result.executed is False
    assert result.request_id



def test_execution_preserves_prepared_request_id():
    prepared = prepare_action("prepare_trip_plan")
    result = execute_action(
        "prepare_trip_plan",
        confirmed=True,
        request_id=prepared.request_id,
        handlers={"prepare_trip_plan": lambda: "ok"},
    )
    assert result.request_id == prepared.request_id
    assert result.executed is True



def test_handler_failure_is_bounded():
    result = execute_action(
        "prepare_trip_plan",
        confirmed=True,
        handlers={"prepare_trip_plan": lambda: (_ for _ in ()).throw(RuntimeError("boom"))},
    )
    assert result.status == "execution_failed"
    assert result.executed is False


def test_confirmed_execution_requires_prepared_request_id():
    result = execute_action(
        "prepare_trip_plan",
        confirmed=True,
        handlers={"prepare_trip_plan": lambda: "should-not-run"},
    )
    assert result.status == "confirmation_required"
    assert result.executed is False
