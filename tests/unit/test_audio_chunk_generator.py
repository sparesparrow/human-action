import json
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import audio_chunk_generator as generator


def test_is_available_requires_sdk_and_api_key(monkeypatch):
    monkeypatch.setattr(generator, "ELEVENLABS_AVAILABLE", True)
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)

    assert generator.is_available() is False

    monkeypatch.setenv("ELEVENLABS_API_KEY", "test-key")
    assert generator.is_available() is True


def test_process_markdown_file_uses_current_sdk_shape(tmp_path, monkeypatch):
    source = tmp_path / "chapter_01-OPTIMIZED.md"
    source.write_text("Test audiobook text.", encoding="utf-8")
    output_dir = tmp_path / "audio"

    convert = MagicMock(return_value=iter([b"abc", b"def"]))
    client = SimpleNamespace(text_to_speech=SimpleNamespace(convert=convert))

    monkeypatch.setattr(generator, "ELEVENLABS_AVAILABLE", True)
    monkeypatch.setattr(generator, "ElevenLabs", MagicMock(return_value=client))
    monkeypatch.setattr(
        generator,
        "VoiceSettings",
        lambda **kwargs: kwargs,
    )

    success, result = generator.process_markdown_file(
        file_path=source,
        output_dir=output_dir,
        api_key="test-key",
        rename_source=False,
    )

    assert success is True
    assert Path(result).read_bytes() == b"abcdef"

    kwargs = convert.call_args.kwargs
    assert kwargs["voice_id"] == generator.DEFAULT_VOICE_ID
    assert kwargs["model_id"] == generator.DEFAULT_MODEL_ID
    assert kwargs["output_format"] == generator.DEFAULT_OUTPUT_FORMAT
    assert kwargs["voice_settings"]["speed"] == 1.0


def test_process_markdown_file_rejects_invalid_speed(tmp_path, monkeypatch):
    source = tmp_path / "chapter_02.md"
    source.write_text("Test", encoding="utf-8")

    monkeypatch.setattr(generator, "ELEVENLABS_AVAILABLE", True)

    success, message = generator.process_markdown_file(
        file_path=source,
        output_dir=tmp_path / "audio",
        api_key="test-key",
        speed=1.5,
    )

    assert success is False
    assert "speed must be between 0.7 and 1.2" in message



def test_process_markdown_files_stitches_requests_and_writes_manifest(tmp_path, monkeypatch):
    first = tmp_path / "chapter_01a-OPTIMIZED.md"
    second = tmp_path / "chapter_01b-OPTIMIZED.md"
    first.write_text("First audiobook chunk.", encoding="utf-8")
    second.write_text("Second audiobook chunk.", encoding="utf-8")
    output_dir = tmp_path / "audio"

    calls = []

    class RawTextToSpeech:
        @contextmanager
        def convert(self, **kwargs):
            calls.append(kwargs)
            number = len(calls)
            yield SimpleNamespace(
                data=iter([f"audio-{number}".encode()]),
                headers={
                    "request-id": f"request-{number}",
                    "character-cost": str(len(kwargs["text"])),
                },
            )

    client = SimpleNamespace(
        text_to_speech=SimpleNamespace(with_raw_response=RawTextToSpeech())
    )
    monkeypatch.setattr(generator, "ELEVENLABS_AVAILABLE", True)
    monkeypatch.setattr(generator, "ElevenLabs", MagicMock(return_value=client))
    monkeypatch.setattr(generator, "VoiceSettings", lambda **kwargs: kwargs)

    result = generator.process_markdown_files(
        [first, second],
        output_dir,
        api_key="test-key",
        rename_source=False,
        skip_existing=False,
    )

    assert result["success"] is True
    assert result["generated"] == 2
    assert result["failed"] == 0
    assert calls[0]["next_text"] == "Second audiobook chunk."
    assert "previous_request_ids" not in calls[0]
    assert calls[1]["previous_request_ids"] == ["request-1"]
    assert (output_dir / "chapter_01a.mp3").read_bytes() == b"audio-1"
    assert (output_dir / "chapter_01b.mp3").read_bytes() == b"audio-2"

    manifest = json.loads(
        (output_dir / "elevenlabs_generation_manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["items"][0]["request_id"] == "request-1"
    assert manifest["items"][1]["request_id"] == "request-2"


def test_process_markdown_files_uses_text_context_after_existing_audio(tmp_path, monkeypatch):
    first = tmp_path / "chapter_01a.md"
    second = tmp_path / "chapter_01b.md"
    first.write_text("Already generated text.", encoding="utf-8")
    second.write_text("New text.", encoding="utf-8")
    output_dir = tmp_path / "audio"
    output_dir.mkdir()
    (output_dir / "chapter_01a.mp3").write_bytes(b"existing")

    calls = []

    class RawTextToSpeech:
        @contextmanager
        def convert(self, **kwargs):
            calls.append(kwargs)
            yield SimpleNamespace(
                data=iter([b"new-audio"]),
                headers={"request-id": "request-new", "character-cost": "9"},
            )

    client = SimpleNamespace(
        text_to_speech=SimpleNamespace(with_raw_response=RawTextToSpeech())
    )
    monkeypatch.setattr(generator, "ELEVENLABS_AVAILABLE", True)
    monkeypatch.setattr(generator, "ElevenLabs", MagicMock(return_value=client))
    monkeypatch.setattr(generator, "VoiceSettings", lambda **kwargs: kwargs)

    result = generator.process_markdown_files(
        [first, second],
        output_dir,
        api_key="test-key",
        rename_source=False,
    )

    assert result["skipped"] == 1
    assert result["generated"] == 1
    assert calls[0]["previous_text"] == "Already generated text."
    assert "previous_request_ids" not in calls[0]
