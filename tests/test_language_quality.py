from services.language_quality import (
    LANGUAGE_RULES,
    language_instruction,
)


def test_language_quality_contract_covers_supported_languages():
    assert set(LANGUAGE_RULES) == {"fr", "en", "wo", "ff"}
    for language in LANGUAGE_RULES:
        instruction = language_instruction(language)
        assert "LANGUE DE SORTIE" in instruction
        assert len(instruction) > 180


def test_wolof_and_pulaar_contracts_avoid_invented_vocabulary():
    wolof = language_instruction("wo").lower()
    pulaar = language_instruction("ff").lower()
    assert "n'invente" in wolof
    assert "n'invente" in pulaar
    assert "traduction littérale" in wolof
    assert "traduction littérale" in pulaar


def test_language_contracts_are_distinct():
    contracts = {lang: language_instruction(lang) for lang in LANGUAGE_RULES}
    assert len(set(contracts.values())) == 4
    assert "LANGUE DE SORTIE : français" in contracts["fr"]
    assert "LANGUE DE SORTIE : English" in contracts["en"]
    assert "LANGUE DE SORTIE : wolof" in contracts["wo"]
    assert "LANGUE DE SORTIE : pulaar" in contracts["ff"]


def test_code_switching_is_not_a_language_fallback():
    assert "majoritairement en wolof" in language_instruction("wo")
    assert "majoritairement en pulaar" in language_instruction("ff")
    assert "N'invente jamais un mot" in language_instruction("wo")
    assert "N'invente pas de vocabulaire pulaar" in language_instruction("ff")

