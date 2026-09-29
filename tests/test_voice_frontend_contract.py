from pathlib import Path


def test_voice_mode_stop_closes_realtime_session():
    html = (Path(__file__).resolve().parents[1] / "templates" / "home.html").read_text(encoding="utf-8")
    marker = "function endVoiceMode(){"
    start = html.rindex(marker)
    end = html.index("\n}", start) + 2
    function = html[start:end]
    assert "stopVoiceCapture();stopVoiceMonitor();" in function
    assert "closeRealtimeVoice();" in function


def test_voice_capture_start_cancels_after_stream_wait():
    html = (Path(__file__).resolve().parents[1] / "templates" / "home.html").read_text(encoding="utf-8")
    marker = "async function startVoiceCapture(){"
    start = html.rindex(marker)
    end = html.index("\n}", start) + 2
    function = html[start:end]
    guard = "if(!voiceConversation||turnId!==voiceTurnId){"
    assert guard in function
    assert function.index(guard) < function.index("if(!ok){")


def test_direct_tts_response_is_scoped_to_current_speech_turn():
    html = (Path(__file__).resolve().parents[1] / "templates" / "home.html").read_text(encoding="utf-8")
    marker = "async function speak(text,btn){"
    start = html.rindex(marker)
    end = html.index("\n}", start) + 2
    function = html[start:end]
    assert "const speechTurn=voiceTtsTurn;" in function
    assert function.count("if(voiceTtsTurn!==speechTurn)return;") >= 5
    assert "if(voiceTtsTurn!==speechTurn){URL.revokeObjectURL(url);return;}" in function


def test_voice_stream_setup_is_scoped_to_current_turn():
    html = (Path(__file__).resolve().parents[1] / "templates" / "home.html").read_text(encoding="utf-8")
    marker = "async function ensureVoiceStream("
    start = html.rindex(marker)
    end = html.index("\n}", start) + 2
    function = html[start:end]
    assert "expectedTurnId=voiceTurnId" in function
    assert "const isCurrent=()=>voiceConversation&&expectedTurnId===voiceTurnId;" in function
    assert "if(!isCurrent()){" in function
    assert "await context.close()" in function
    assert "const ok=await ensureVoiceStream(turnId);" in function


def test_speech_synthesis_callbacks_ignore_stale_tts_turns():
    html = (Path(__file__).resolve().parents[1] / "templates" / "home.html").read_text(encoding="utf-8")
    marker = "function speakFallback(text,btn,speechTurn=voiceTtsTurn){"
    start = html.rindex(marker)
    end = html.index("\n}", start) + 2
    function = html[start:end]
    assert "const finish=()=>{if(voiceTtsTurn!==speechTurn)return;finishSpeech(btn);};" in function
    assert "utterance.onend=finish;" in function
    assert "utterance.onerror=finish;" in function
