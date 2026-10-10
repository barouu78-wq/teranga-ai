"""Transcription vocale : le nom du fichier envoyé au fournisseur suit le vrai format de l'audio.

Un iPhone enregistre en audio/mp4 ; l'ancien code le nommait « .webm » et le fournisseur le refusait.
"""

import io
import os
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("OPENAI_API_KEY", "test-key")

import app as app_module  # noqa: E402
from routes.stt import audio_filename  # noqa: E402

MP4 = b"\x00\x00\x00\x20ftypM4A \x00\x00\x00\x00M4A mp42isom" + b"\x00" * 40
WEBM = b"\x1a\x45\xdf\xa3\x9f\x42\x86\x81\x01" + b"\x00" * 40
OGG = b"OggS\x00\x02" + b"\x00" * 40
WAV = b"RIFF\x24\x08\x00\x00WAVEfmt " + b"\x00" * 40
MP3 = b"ID3\x04\x00" + b"\x00" * 40


def test_filename_follows_the_real_audio_format_whatever_the_client_says():
    assert audio_filename(MP4, "teranga-voice.webm") == "voice.m4a"
    assert audio_filename(WEBM, "teranga-voice.m4a") == "voice.webm"
    assert audio_filename(OGG) == "voice.ogg" and audio_filename(WAV) == "voice.wav" and audio_filename(MP3) == "voice.mp3"
    assert audio_filename(b"fLaC" + b"\x00" * 20) == "voice.flac"


def test_unknown_audio_keeps_a_safe_default_and_never_uses_a_hostile_name():
    assert audio_filename(b"fake-audio") == "voice.webm"
    assert audio_filename(b"fake-audio", "../../etc/passwd") == "voice.webm"
    assert audio_filename(b"fake-audio", "voice.ogg") == "voice.ogg"
    assert audio_filename(b"") == "voice.webm"


def test_stt_route_sends_the_corrected_name_to_the_provider(monkeypatch):
    seen = {}

    def fake_create(**kwargs):
        seen["name"] = kwargs["file"].name
        return SimpleNamespace(text="bonjour")

    monkeypatch.setattr(app_module.client.audio.transcriptions, "create", fake_create)
    client = app_module.app.test_client()
    token = client.get("/csrf").get_json()["token"]
    for raw, expected in ((MP4, "voice.m4a"), (WEBM, "voice.webm")):
        response = client.post(
            "/stt",
            data={"audio": (io.BytesIO(raw), "teranga-voice.webm"), "language": "fr"},
            headers={"Origin": app_module.SITE_URL, "X-CSRF-Token": token},
            content_type="multipart/form-data",
            environ_base={"REMOTE_ADDR": "203.0.113.190"},
        )
        assert response.status_code == 200 and response.get_json()["text"] == "bonjour"
        assert seen["name"] == expected


def test_browser_names_the_recording_after_its_real_type():
    source = (Path(__file__).resolve().parents[1] / "static" / "home.js").read_text(encoding="utf-8")
    assert "function voiceFileName(type)" in source
    assert "form.append('audio',blob,voiceFileName(blob.type));" in source
    assert "'teranga-voice.webm');" not in source.split("function voiceFileName", 1)[1].split("async function postVoiceAudio", 1)[1]
    assert "'teranga-voice.m4a'" in source


def test_service_worker_version_was_bumped_with_home_js():
    sw = (Path(__file__).resolve().parents[1] / "static" / "sw.js").read_text(encoding="utf-8")
    assert "const VERSION = 'teranga-v9';" in sw
