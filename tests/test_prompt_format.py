from services.chat_payload_service import _format_memory, _format_plan
from services.orchestrator import AgentPlan


def test_format_memory_renders_each_fact_once():
    memory = {
        "place": "goree", "budget": "100000 fcfa",
        "temporary": {
            "place": "goree", "budget": "100000 fcfa", "family": True,
            "constraints": ["budget=100000 fcfa", "famille", "plage"],
        },
        "durable_candidates": ["les plages calmes"],
        "source": "recent_conversation",
    }
    text = _format_memory(memory)
    assert text == "lieu = goree ; budget = 100000 fcfa ; famille = oui ; autres contraintes = plage ; préférences exprimées = les plages calmes"
    assert "recent_conversation" not in text and "temporary" not in text


def test_format_memory_empty():
    assert _format_memory({}) == "aucune"
    assert _format_memory(None) == "aucune"


def test_format_plan_matches_final_request_decisions():
    plan = AgentPlan(model="gpt-internal", steps=("prepare_context", "web_retrieval", "generate_response", "finalize"), use_web=True)
    text = _format_plan(plan, planner=True, use_web=False)
    assert "gpt-internal" not in text
    assert "recherche web : non" in text and "→ recherche web" not in text
    assert "construire un plan → répondre" in text
