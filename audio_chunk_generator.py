#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ElevenLabs text-to-speech processor.

Converts one Markdown chunk to audio with the current ElevenLabs Python SDK.
The module is intentionally import-safe so local/offline test runs can proceed
without an ElevenLabs API key.
"""

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Optional

DEFAULT_VOICE_ID = "OJtLHqR5g0hxcgc27j7C"
DEFAULT_MODEL_ID = "eleven_multilingual_v2"
DEFAULT_OUTPUT_FORMAT = "mp3_44100_128"

ELEVENLABS_AVAILABLE = False
try:
    from elevenlabs import VoiceSettings
    from elevenlabs.client import ElevenLabs

    ELEVENLABS_AVAILABLE = True
except ImportError:
    VoiceSettings = None
    ElevenLabs = None

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def is_available(api_key: Optional[str] = None) -> bool:
    """Return True when both the SDK and an API key are available."""
    return ELEVENLABS_AVAILABLE and bool(api_key or os.getenv("ELEVENLABS_API_KEY"))


def _validate_unit_interval(name: str, value: float) -> None:
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} must be between 0.0 and 1.0, got {value}")


def _validate_speed(speed: float) -> None:
    if not 0.7 <= speed <= 1.2:
        raise ValueError(f"speed must be between 0.7 and 1.2, got {speed}")


def _extension_for_output_format(output_format: str) -> str:
    codec = output_format.split("_", 1)[0].lower()
    if codec in {"mp3", "wav", "pcm", "ulaw", "alaw", "opus"}:
        return codec
    return "mp3"


def process_markdown_file(
    file_path,
    output_dir,
    voice_id: str = DEFAULT_VOICE_ID,
    model_id: str = DEFAULT_MODEL_ID,
    stability: float = 0.5,
    similarity_boost: float = 0.75,
    style: float = 0.0,
    speed: float = 1.0,
    output_format: str = DEFAULT_OUTPUT_FORMAT,
    use_speaker_boost: bool = True,
    api_key: Optional[str] = None,
    rename_source: bool = True,
):
    """
    Generate audio for one Markdown file.

    Returns:
        Tuple (success, output_file_path_or_error_message)
    """
    if not ELEVENLABS_AVAILABLE:
        return False, "ElevenLabs SDK is not installed"

    resolved_api_key = api_key or os.getenv("ELEVENLABS_API_KEY")
    if not resolved_api_key:
        return False, "ELEVENLABS_API_KEY is not configured"

    try:
        _validate_unit_interval("stability", stability)
        _validate_unit_interval("similarity_boost", similarity_boost)
        _validate_unit_interval("style", style)
        _validate_speed(speed)

        source_path = Path(file_path)
        destination_dir = Path(output_dir)
        destination_dir.mkdir(parents=True, exist_ok=True)

        base_name = source_path.stem.replace("-OPTIMIZED", "")
        extension = _extension_for_output_format(output_format)
        output_file = destination_dir / f"{base_name}.{extension}"

        text_content = source_path.read_text(encoding="utf-8")
        if not text_content.strip():
            return False, f"File {source_path.name} is empty"

        logger.info("Generating ElevenLabs audio: %s -> %s", source_path.name, output_file.name)

        client = ElevenLabs(api_key=resolved_api_key)
        audio = client.text_to_speech.convert(
            voice_id=voice_id,
            text=text_content,
            model_id=model_id,
            output_format=output_format,
            voice_settings=VoiceSettings(
                stability=stability,
                similarity_boost=similarity_boost,
                style=style,
                use_speaker_boost=use_speaker_boost,
                speed=speed,
            ),
        )

        bytes_written = 0
        with output_file.open("wb") as audio_file:
            for chunk in audio:
                if chunk:
                    audio_file.write(chunk)
                    bytes_written += len(chunk)

        if bytes_written == 0:
            output_file.unlink(missing_ok=True)
            raise RuntimeError(f"ElevenLabs returned no audio bytes for {source_path.name}")

        if rename_source:
            processed_path = source_path.parent / f"AUDIO_GENERATED-{source_path.name}"
            try:
                source_path.rename(processed_path)
            except OSError as exc:
                logger.warning("Could not rename processed source %s: %s", source_path.name, exc)

        logger.info("Generated %s (%d bytes)", output_file, bytes_written)
        return True, str(output_file)

    except Exception as exc:
        source_name = Path(file_path).name
        error_msg = f"Error processing {source_name}: {exc}"
        logger.error(error_msg)
        return False, error_msg


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Generate speech from a Markdown file with ElevenLabs",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("file", help="Markdown file to synthesize")
    parser.add_argument("-o", "--output-dir", default="./data/5-audio-chunks")
    parser.add_argument("-v", "--voice-id", default=DEFAULT_VOICE_ID)
    parser.add_argument("-m", "--model-id", default=DEFAULT_MODEL_ID)
    parser.add_argument("--output-format", default=DEFAULT_OUTPUT_FORMAT)
    parser.add_argument("--stability", type=float, default=0.5)
    parser.add_argument("--similarity-boost", type=float, default=0.75)
    parser.add_argument("--style", type=float, default=0.0)
    parser.add_argument("--speed", type=float, default=1.0)
    parser.add_argument(
        "--no-speaker-boost",
        action="store_true",
        help="Disable ElevenLabs speaker boost",
    )
    parser.add_argument(
        "--api-key",
        help="API key; defaults to ELEVENLABS_API_KEY",
    )
    parser.add_argument(
        "--keep-source-name",
        action="store_true",
        help="Do not rename the processed Markdown file",
    )
    args = parser.parse_args()

    success, result = process_markdown_file(
        file_path=args.file,
        output_dir=args.output_dir,
        voice_id=args.voice_id,
        model_id=args.model_id,
        stability=args.stability,
        similarity_boost=args.similarity_boost,
        style=args.style,
        speed=args.speed,
        output_format=args.output_format,
        use_speaker_boost=not args.no_speaker_boost,
        api_key=args.api_key,
        rename_source=not args.keep_source_name,
    )

    if success:
        logger.info("Processing completed: %s", result)
        return 0

    logger.error("Processing failed: %s", result)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
