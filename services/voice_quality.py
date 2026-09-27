"""Centralized voice quality rules for Teranga AI."""

VOICE_LANGUAGE_RULES = {
    "fr": {
        "name": "français",
        "voice": "Réponds en français naturel, oral et concis.",
        "stt": "Transcris fidèlement le français parlé. Conserve les noms, chiffres, lieux et mots sénégalais.",
        "tts": "Voix naturelle, chaleureuse et conversationnelle. Débit fluide, micro-pauses naturelles. Prononce soigneusement les noms sénégalais. Ne lis jamais markdown, URL, emojis ou symboles techniques.",
    },
    "en": {
        "name": "anglais",
        "voice": "Reply in natural spoken English, concise and conversational.",
        "stt": "Transcribe spoken English faithfully. Preserve Senegalese names, places, numbers and local terms.",
        "tts": "Warm, natural conversational voice. Smooth pace with short natural pauses. Pronounce Senegalese names carefully. Never read markdown, URLs, emojis or technical symbols.",
    },
    "wo": {
        "name": "wolof",
        "voice": "Wax ci wolof bu naturel te leer. Bul tekki mot a mot. Bul sos baat bu wolof bu nga xamul.",
        "stt": "Transcris li nit wax ci Wolof ci anam bu wor. Bul reformule te bul sos baat. Denc tur yi, lim yi ak dëkk yi.",
        "tts": "Wax ak baat bu naturel te neex, mel ni waxtaan ci kanam ak kanam. Débit bu yomb, noppi yu gàtt, intonation bu naturel. Bul jàng markdown, URL walla simbol yu teknikal.",
    },
    "ff": {
        "name": "pulaar",
        "voice": "Reponds en pulaar naturel et oral. Evite la traduction littérale. N'invente pas de vocabulaire pulaar.",
        "stt": "Transcris fidèlement le pulaar parlé. Ne reformule pas et n'invente pas de vocabulaire.",
        "tts": "Voix humaine, chaleureuse et naturelle. Débit fluide, petites pauses naturelles. Respecte au mieux la prononciation pulaar. Ne lis jamais markdown, URL ou signes techniques.",
    },
}

CODE_SWITCHING_RULE = (
    "Si la personne mélange plusieurs langues, comprends le mélange sans le corriger. "
    "Réponds majoritairement dans la langue demandée ou dominante, mais conserve les mots wolof, "
    "pulaar, français ou anglais naturels lorsqu'ils portent du sens. Ne traduis pas automatiquement "
    "les noms propres ou expressions culturelles."
)

def voice_instruction(language):
    rule = VOICE_LANGUAGE_RULES.get(language, VOICE_LANGUAGE_RULES["fr"])
    return f"{rule['voice']} {CODE_SWITCHING_RULE} Réponds comme dans une vraie conversation orale."

def transcription_prompt(language):
    rule = VOICE_LANGUAGE_RULES.get(language, VOICE_LANGUAGE_RULES["fr"])
    return rule["stt"] + " " + CODE_SWITCHING_RULE

def tts_instruction(language):
    return VOICE_LANGUAGE_RULES.get(language, VOICE_LANGUAGE_RULES["fr"])["tts"]
