from services.text import clean_answer


def test_clean_answer_removes_markdown_and_limits_length():
    raw = "## Titre\n\n**Bonjour**\n\n- Dakar\n- Sénégal"
    # Les listes gardent une puce « • », plus lisible qu'une ligne nue.
    assert clean_answer(raw) == "Titre\n\nBonjour\n• Dakar\n• Sénégal"


def test_clean_answer_strips_inline_code_and_extra_blank_lines():
    assert clean_answer("Salut `Dakar`\n\n\n\nMerci") == "Salut Dakar\n\nMerci"
