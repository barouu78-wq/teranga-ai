from services.voice_quality import voice_instruction, transcription_prompt, tts_instruction


def test_all_languages_have_voice_rules():
    for language in ("fr", "en", "wo", "ff"):
        assert voice_instruction(language)
        assert transcription_prompt(language)
        assert tts_instruction(language)


def test_wolof_and_pulaar_guard_against_invention():
    assert "Bul sos" in voice_instruction("wo")
    assert "N'invente pas" in voice_instruction("ff")


def test_code_switching_is_preserved():
    text = voice_instruction("wo")
    assert "mélange" in text
    assert "noms propres" in text
