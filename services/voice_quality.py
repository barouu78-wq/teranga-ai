VOICE_LANGUAGE_RULES = {
    "fr": ("francais", "Reponds en francais naturel, oral et concis.", "Transcris fidelement le francais parle."),
    "en": ("English", "Reply in natural spoken English, concise and conversational.", "Transcribe spoken English faithfully."),
    "wo": ("wolof", "Wax ci wolof bu naturel te leer. Bul tekki mot a mot. Bul sos baat bu wolof bu nga xamul.", "Transcris li nit wax ci wolof ci anam bu wor. Bul reformile te bul sos baat."),
    "ff": ("pulaar", "Reponds en pulaar naturel et oral. Evite la traduction litterale. N'invente pas de vocabulaire pulaar.", "Transcris fidelement le pulaar parle. Ne reformule pas et n'invente pas de vocabulaire."),
}

CODE_SWITCHING_RULE = "Si la personne mélange plusieurs langues, comprends le mélange sans le corriger. Réponds majoritairement dans la langue demandée ou dominante, mais conserve les mots wolof, pulaar, francais ou anglais naturels lorsqu'ils portent du sens. Ne traduis pas automatiquement les noms propres ou expressions culturelles."
    
def voice_instruction(language):
    name, speech, _ = VOICE_LANGUAGE_RULES.get(language, VOICE_LANGUAGE_RULES["fr"])
    return f"LANGUE VOCALE : {name}. {speech} {CODE_SWITCHING_RULE} Fais des phrases courtes et completes. Ne lis jamais markdown, URL, listes ou symboles techniques a voix haute. Si une phrase est ambigue, demande brievement plutot que d'inventer."

def transcription_prompt(language):
    name, _, stt = VOICE_LANGUAGE_RULES.get(language, VOICE_LANGUAGE_RULES["fr"])
    return f"LANGUE AUDIO : {name}. {stt} Si le locuteur melange les langues, conserve le code-switching au lieu de traduire. Conserve noms propres, lieux, chiffres et termes senegalais. Contexte : Senegal, Dakar, AIBD, Goree, Rufisque, Thies, Saint-Louis, Saly, Casamance, FCFA, BCEAO, Wolof, Pulaar."

def tts_instruction(language):
    name, speech, _ = VOICE_LANGUAGE_RULES.get(language, VOICE_LANGUAGE_RULES["fr"])
    return f"Voix conversationnelle naturelle en {name}. {speech} Articulation claire, debit naturel, micro-pauses et intonation vivante. Prononce soigneusement les noms senegalais. Ne lis jamais markdown, URL, emojis, listes ou signes techniques."
