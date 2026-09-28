from pathlib import Path


def test_voice_mode_stop_closes_realtime_session():
    html = (Path(__file__).resolve().parents[1] / "templates" / "home.html").read_text(encoding="utf-8")
    marker = "function endVoiceMode(){"
    start = html.index(marker)
    end = html.index("\n}", start) + 2
    function = html[start:end]
    assert "stopVoiceCapture();stopVoiceMonitor();" in function
    assert "closeRealtimeVoice();" in function
