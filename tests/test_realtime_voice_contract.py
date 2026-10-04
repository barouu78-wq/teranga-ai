from home_source import home_source
from pathlib import Path


def test_realtime_start_aborts_if_voice_mode_was_stopped():
    html = home_source()
    start = html.index("async function startRealtimeVoice(){")
    end = html.index("\n}", start) + 2
    function = html[start:end]
    assert "if(!voiceConversation||!autoVoice)" in function
    assert "stream.getTracks().forEach(t=>{try{t.stop();}catch(_){} });" in function or "stream.getTracks().forEach(t=>{try{t.stop();}catch(_){}});" in function
    assert "realtimePc=new RTCPeerConnection();" in function


def test_realtime_start_requires_active_voice_mode_before_microphone_access():
    html = home_source()
    start = html.index("async function startRealtimeVoice(){")
    guard = html.index("if(!voiceConversation||!autoVoice)return false;", start)
    get_user_media = html.index("navigator.mediaDevices.getUserMedia", start)
    assert guard < get_user_media


def test_realtime_callbacks_are_scoped_to_current_session():
    html = home_source()
    start = html.index("async function startRealtimeVoice(){")
    end = html.index("\n}\nasync function stopLegacyVoiceForRealtime", start) + 2
    function = html[start:end]
    assert "const sessionId=++realtimeSessionId;" in function
    assert "if(sessionId!==realtimeSessionId)return;" in function
    assert "if(sessionId===realtimeSessionId)closeRealtimeVoice();" in function


def test_closing_realtime_invalidates_existing_callbacks():
    html = home_source()
    start = html.index("function closeRealtimeVoice(){")
    end = html.index("\n}", start) + 2
    function = html[start:end]
    assert "realtimeSessionId++;" in function


def test_realtime_handshake_rechecks_session_after_network_waits():
    html = home_source()
    start = html.index("async function startRealtimeVoice(){")
    end = html.index("\n}\nasync function stopLegacyVoiceForRealtime", start) + 2
    function = html[start:end]
    assert function.count("if(sessionId!==realtimeSessionId)return false;") >= 5
    assert "if(sessionId!==realtimeSessionId||!realtimePc)return false;" in function
    assert "if(sessionId!==realtimeSessionId)return false;\n    realtimeStarting=false;" in function


def test_browser_voice_stop_cancels_pending_speech_result():
    html = home_source()
    end_start = html.rindex("function endVoiceMode(){")
    end_end = html.index("\n}", end_start) + 2
    end_function = html[end_start:end_end]
    assert "clearVoiceSilence();" in end_function
    assert "voiceDraft='';" in end_function

    setup_start = html.rindex("function setupMic(){")
    setup_end = html.index("\n}\nmic.onclick=", setup_start) + 2
    setup = html[setup_start:setup_end]
    assert "if(!voiceConversation)return;" in setup
    assert "if(!voiceConversation)return;\n          const spoken=voiceDraft.trim();" in setup


def test_stt_response_rechecks_voice_turn_after_network_waits():
    html = home_source()
    start = html.index("async function postVoiceAudio(")
    end = html.index("\n}\nfunction finishVoiceRecording", start) + 2
    function = html[start:end]
    assert function.count("if(!voiceConversation||turnId!==voiceTurnId)return;") >= 3
    assert "await refreshCsrf();\n      if(!voiceConversation||turnId!==voiceTurnId)return;" in function
