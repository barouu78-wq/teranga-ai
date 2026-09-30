from services.chat_service import select_chat_model


def test_simple_chat_stays_on_luna():
    assert select_chat_model({"planner": False}, "gpt-5.6-luna") == "gpt-5.6-luna"


def test_planner_chat_uses_stronger_model():
    assert select_chat_model({"planner": True}, "gpt-5.6-luna") == "gpt-5.6-sol"


def test_custom_complex_model_can_be_selected():
    assert select_chat_model({"planner": True}, "gpt-5.6-luna", "gpt-5.6-terra") == "gpt-5.6-terra"


def test_existing_non_luna_model_is_not_overridden():
    assert select_chat_model({"planner": True}, "custom-model", "gpt-5.6-sol") == "custom-model"
