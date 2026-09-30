from services.youth_projects import build_project_brief, detect_project_category


def test_detect_project_category_for_local_food_project():
    assert detect_project_category("Je veux vendre du jus naturel à Thiès") == "food"


def test_project_brief_turns_minimal_inputs_into_action_plan():
    brief = build_project_brief(
        idea="Vendre du jus naturel à Thiès",
        city="Thiès",
        budget_fcfa=50000,
        skills="cuisine",
        available_time="week-end",
        goal_fcfa=100000,
    )

    assert brief["category"] == "food"
    assert brief["budget_fcfa"] == 50000
    assert brief["goal_fcfa"] == 100000
    assert brief["stage"] == "idea"
    assert len(brief["steps"]) == 5
    assert "Thiès" in brief["steps"][0]["action"]
    assert brief["next_action"]
