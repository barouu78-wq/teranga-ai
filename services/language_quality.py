"""Language quality rules for Teranga AI.

This module keeps language-specific behavior explicit and testable. It does not
attempt to machine-translate Wolof or Pulaar; it tells the model to preserve
natural usage and to avoid inventing vocabulary when uncertain.
"""

LANGUAGE_RULES = {
    "fr": {
        "name": "français",
        "instruction": (
            "Réponds en français naturel et idiomatique. Évite les calques de "
            "l'anglais et les formulations artificielles. Garde les noms de lieux, "
            "personnes, plats et expressions sénégalaises dans leur forme usuelle. "
            "Accorde correctement les phrases et utilise une ponctuation naturelle."
        ),
        "avoid": "anglais, wolof ou pulaar non nécessaires dans une phrase française",
    },
    "en": {
        "name": "English",
        "instruction": (
            "Reply in natural, idiomatic English. Do not translate French sentence "
            "structure word-for-word. Keep Senegalese names, places, dishes and "
            "cultural terms in their established forms. Use natural English punctuation "
            "and concise conversational phrasing."
        ),
        "avoid": "French sentence structure or unnecessary French filler",
    },
    "wo": {
        "name": "wolof",
        "instruction": (
            "Réponds en wolof naturel, simple et compréhensible. Priorité à une "
            "formulation réellement utilisée plutôt qu'à une traduction littérale "
            "du français ou de l'anglais. Conserve les noms propres, lieux, plats "
            "et termes culturels dans leur forme usuelle. N'invente jamais un mot "
            "wolof pour combler un manque : si un terme spécialisé n'est pas sûr, "
            "utilise une formulation wolof sûre et explique brièvement le terme "
            "étranger si nécessaire. Si l'utilisateur mélange wolof et français, "
            "comprends le code-switching mais réponds majoritairement en wolof. "
            "Respecte l'orthographe et les variantes présentes dans le message "
            "lorsqu'elles sont claires."
        ),
        "avoid": "français traduit mot à mot, faux mots wolof ou longues phrases françaises",
    },
    "ff": {
        "name": "pulaar (Fuuta Tooro)",
        "instruction": (
            "Réponds en pulaar naturel de référence pour le contexte sénégalais, "
            "en privilégiant une formulation sûre plutôt qu'une traduction littérale "
            "du français. Respecte les noms propres, lieux et termes culturels. "
            "N'invente pas de vocabulaire pulaar lorsqu'un terme est incertain : "
            "reformule simplement ou conserve le terme propre si nécessaire. "
            "Si l'utilisateur mélange pulaar et français, comprends le mélange mais "
            "réponds majoritairement en pulaar. Respecte l'orthographe fournie par "
            "l'utilisateur quand elle est claire et évite de normaliser abusivement "
            "une variante sans raison."
        ),
        "avoid": "français traduit mot à mot, vocabulaire pulaar inventé ou mélange excessif",
    },
}


def language_instruction(language):
    """Return a complete, explicit language contract for one supported language."""
    rules = LANGUAGE_RULES.get(language, LANGUAGE_RULES["fr"])
    return (
        f"LANGUE DE SORTIE : {rules['name']}. "
        f"{rules['instruction']} "
        f"À éviter : {rules['avoid']}. "
        "Avant d'envoyer la réponse, vérifie silencieusement que la langue demandée "
        "reste dominante, que les phrases sont terminées et que tu n'as pas fabriqué "
        "de vocabulaire. Ne parle pas de cette vérification dans la réponse."
    )


def is_supported_language(language):
    """Return whether a language is supported by the chat language engine."""
    return language in LANGUAGE_RULES


def language_test_cases():
    """Small stable prompts used by automated language regression tests."""
    return {
        "fr": "Explique en français pourquoi Gorée est importante.",
        "en": "Explain in English why Gorée is important.",
        "wo": "Wax ma ci wolof lu tax Gorée am solo.",
        "ff": "Fiytu am Pulaar ko fii Gorée waɗi maanaa.",
    }
