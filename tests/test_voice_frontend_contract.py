from home_source import home_source


def test_voice_mode_stop_releases_the_microphone():
    html = home_source()
    marker = "function endVoiceMode(){"
    start = html.rindex(marker)
    end = html.index("\n}", start) + 2
    function = html[start:end]
    assert "stopVoiceCapture();stopVoiceMonitor();" in function
    assert "voiceConversation=false" in function


def test_voice_capture_start_cancels_after_stream_wait():
    html = home_source()
    marker = "async function startVoiceCapture(){"
    start = html.rindex(marker)
    end = html.index("\n}", start) + 2
    function = html[start:end]
    guard = "if(!voiceConversation||turnId!==voiceTurnId){"
    assert guard in function
    assert function.index(guard) < function.index("if(!ok){")


def test_direct_tts_response_is_scoped_to_current_speech_turn():
    html = home_source()
    marker = "async function speak(text,btn){"
    start = html.rindex(marker)
    end = html.index("\n}", start) + 2
    function = html[start:end]
    assert "const speechTurn=voiceTtsTurn;" in function
    # Chaque étape après une attente vérifie le tour via stale(), qui compare
    # voiceTtsTurn et réactive le bouton « Écouter » si le tour est dépassé.
    assert "const stale=()=>{if(voiceTtsTurn!==speechTurn)" in function
    assert function.count("if(stale())return;") >= 5
    assert "if(voiceTtsTurn!==speechTurn){URL.revokeObjectURL(url);return;}" in function


def test_queued_tts_uses_item_generation_after_network_wait():
    html = home_source()
    marker = "async function playVoiceTtsQueue(){"
    start = html.rindex(marker)
    end = html.index("\n}", start) + 2
    function = html[start:end]
    assert "if(item.turn!==voiceTtsTurn||!autoVoice)return;" in function
    assert "if(voiceTtsTurn!==speechTurn)return;" not in function
