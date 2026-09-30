from flask import Flask

from routes.youth_projects import register_youth_project_route


def test_youth_opportunity_route_lists_matching_sources():
    app = Flask(__name__)

    def sanitize_text(value, max_len):
        return str(value or "")[:max_len]

    register_youth_project_route(
        app,
        {
            "require_json_post": lambda fn: fn,
            "sanitize_text": sanitize_text,
            "build_project_brief": lambda **kwargs: {},
            "advance_project_stage": lambda project, stage=None: project,
            "find_youth_opportunities": lambda category="", city="": [{"title": "BE YES", "organization": "DER/FJ"}],
        },
    )

    client = app.test_client()
    response = client.get("/opportunities?category=digital")
    assert response.status_code == 200
    assert b"BE YES" in response.data
    assert b"DER/FJ" in response.data


def test_youth_project_plan_route_builds_project():
    app = Flask(__name__)

    def require_json_post(fn):
        return fn

    def sanitize_text(value, max_len):
        return str(value or "")[:max_len]

    def advance_project_stage(project, stage=None):
        project = dict(project)
        project["stage"] = "validation"
        return project

    def build_project_brief(**kwargs):
        return {
            "name": kwargs["idea"],
            "category": "food",
            "city": kwargs["city"],
            "budget_fcfa": 50000,
            "goal_fcfa": 100000,
        }

    register_youth_project_route(
        app,
        {
            "require_json_post": require_json_post,
            "sanitize_text": sanitize_text,
            "build_project_brief": build_project_brief,
            "advance_project_stage": advance_project_stage,
            "max_message_length": 2000,
        },
    )

    client = app.test_client()
    response = client.post(
        "/api/projects/plan",
        json={
            "idea": "Vendre du jus naturel",
            "city": "Thiès",
            "budget_fcfa": 50000,
            "goal_fcfa": 100000,
        },
    )

    assert response.status_code == 200
    assert response.get_json()["project"]["name"] == "Vendre du jus naturel"


def test_youth_project_plan_route_rejects_empty_idea():
    app = Flask(__name__)

    def require_json_post(fn):
        return fn

    register_youth_project_route(
        app,
        {
            "require_json_post": require_json_post,
            "sanitize_text": lambda value, max_len: str(value or "")[:max_len],
            "build_project_brief": lambda **kwargs: {},
        },
    )

    client = app.test_client()
    response = client.post("/api/projects/plan", json={"idea": "   "})

    assert response.status_code == 400
    assert response.get_json()["error"]


def test_youth_project_advance_route_moves_project_forward():
    app = Flask(__name__)

    def require_json_post(fn):
        return fn

    register_youth_project_route(
        app,
        {
            "require_json_post": require_json_post,
            "sanitize_text": lambda value, max_len: str(value or "")[:max_len],
            "build_project_brief": lambda **kwargs: {},
            "advance_project_stage": lambda project, stage=None: project,
            "advance_project_stage": lambda project, stage=None: {**project, "stage": "validation"},
        },
    )

    response = app.test_client().post(
        "/api/projects/advance",
        json={"project": {"name": "Jus naturel", "stage": "idea"}},
    )

    assert response.status_code == 200
    assert response.get_json()["project"]["stage"] == "validation"
