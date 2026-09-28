from pathlib import Path


def test_realtime_start_aborts_if_voice_mode_was_stopped():
    html = (Path(__file__).resolve().parents[1] / "templates" / "home.html").read_text(encoding="utf-8")
    start = html.index("async function startRealtimeVoice(){")
    end = html.index("\n}", start) + 2
    function = html[start:end]
    assert "if(!voiceConversation||!autoVoice)" in function
    assert "stream.getTracks().forEach(t=>{try{t.stop();}catch(_){} });" in function or "stream.getTracks().forEach(t=>{try{t.stop();}catch(_){}});" in function
    assert "realtimePc=new RTCPeerConnection();" in function


def test_realtime_start_requires_active_voice_mode_before_microphone_access():
    html = (Path(__file__).resolve().parents[1] / "templates" / "home.html").read_text(encoding="utf-8")
    start = html.index("async function startRealtimeVoice(){")
    guard = html.index("if(!voiceConversation||!autoVoice)return false;", start)
    get_user_media = html.index("navigator.mediaDevices.getUserMedia", start)
    assert guard < get_user_media
