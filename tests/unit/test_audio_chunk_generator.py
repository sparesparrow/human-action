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
