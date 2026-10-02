from services.intelligence import build_structured_memory

def test_structured_memory_separates_temporary_context():
    memory = build_structured_memory({
        "query": "Je vais à Dakar pour 3 jours avec mes enfants",
        "place": "dakar",
        "duration": "3 jours",
        "children": 2,
        "constraints": ["durée=3 jours", "enfants=2", "famille"],
    })
    assert memory["temporary"]["place"] == "dakar"
    assert memory["temporary"]["duration"] == "3 jours"
    assert memory["temporary"]["children"] == 2
    assert memory["temporary"]["family"] is True
    assert memory["durable_candidates"] == []

def test_structured_memory_only_marks_explicit_preferences_as_candidates():
    memory = build_structured_memory({
        "query": "Je préfère les trajets en train",
        "place": "dakar",
    })
    assert memory["temporary"]["place"] == "dakar"
    assert memory["durable_candidates"] == ["les trajets en train"]

def test_structured_memory_is_bounded():
    memory = build_structured_memory({
        "query": "J'aime " + ("x" * 500),
        "constraints": [f"c{i}" for i in range(20)],
    })
    assert len(memory["temporary"]["constraints"]) == 8
    assert len(memory["durable_candidates"][0]) <= 120
