VOICE_LANGUAGE_RULES = {}

def voice_instruction(language):
    return f"LANGUE VOCALE : {language}."

def transcription_prompt(language):
    return f"LANGUE AUDIO : {language}."

def tts_instruction(language):
    return f"Voix conversationnelle naturelle en {language}."
