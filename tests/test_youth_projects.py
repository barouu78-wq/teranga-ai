from services.youth_projects import build_project_brief, detect_project_category, find_project_partners


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


def test_project_stage_advances_one_step_at_a_time():
    from services.youth_projects import advance_project_stage

    project = build_project_brief(idea="Vendre du jus naturel", city="Thiès")
    validation = advance_project_stage(project)
    assert validation["stage"] == "validation"
    assert validation["stage_label"] == "Validation"

    prototype = advance_project_stage(validation)
    assert prototype["stage"] == "prototype"
    assert prototype["stage_index"] == 2

def test_project_stage_does_not_skip_steps():
    from services.youth_projects import advance_project_stage

    project = build_project_brief(idea="Vendre du jus naturel")
    updated = advance_project_stage(project, "revenue")
    assert updated["stage"] == "validation"


def test_project_brief_includes_a_follow_up_tracking_model():
    brief = build_project_brief(
        idea="Vendre du jus naturel",
        goal_fcfa=100000,
    )
    assert brief["tracking"]["period"] == "30 jours"
    assert "Ventes réalisées" in brief["tracking"]["indicators"]
    assert brief["tracking"]["weekly_checklist"]


def test_partner_directory_matches_project_category():
    partners = find_project_partners("digital")
    assert partners
    assert any("Orange" in partner["name"] for partner in partners)
