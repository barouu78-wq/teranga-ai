from services.images import topic_wikipedia_titles


def test_topic_wikipedia_titles_resolves_known_places():
    assert topic_wikipedia_titles("Montre-moi des photos de Gorée") == ["Île de Gorée"]
    assert topic_wikipedia_titles("photos de Saint-Louis et du Djoudj", limit=2) == [
        "Saint-Louis (Sénégal)",
        "Parc national des oiseaux du Djoudj",
    ]


def test_topic_wikipedia_titles_ignores_unknown_topics():
    assert topic_wikipedia_titles("Quelle est l'histoire du Sénégal ?") == []
