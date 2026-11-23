from services.action_executor import ALLOWED_ACTIONS, prepare_action


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
