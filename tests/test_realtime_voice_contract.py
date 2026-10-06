from home_source import home_source


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
