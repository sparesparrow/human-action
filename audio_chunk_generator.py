#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ElevenLabs text-to-speech processor.

Supports both one-off Markdown synthesis and sequential long-form audiobook
generation with continuity context/request stitching. The module is import-safe
so local/offline tests do not require an ElevenLabs API key.
"""

import argparse
import json
import logging
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional

DEFAULT_VOICE_ID = "OJtLHqR5g0hxcgc27j7C"
DEFAULT_MODEL_ID = "eleven_multilingual_v2"
DEFAULT_OUTPUT_FORMAT = "mp3_44100_128"
MODEL_CHARACTER_LIMITS = {
    "eleven_multilingual_v2": 10_000,
    "eleven_v3": 5_000,
}

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


def _validate_voice_settings(
    stability: float,
    similarity_boost: float,
    style: float,
    speed: float,
) -> None:
    _validate_unit_interval("stability", stability)
    _validate_unit_interval("similarity_boost", similarity_boost)
    _validate_unit_interval("style", style)
    _validate_speed(speed)


def _voice_settings(
    stability: float,
    similarity_boost: float,
    style: float,
    speed: float,
    use_speaker_boost: bool,
):
    return VoiceSettings(
        stability=stability,
        similarity_boost=similarity_boost,
        style=style,
        use_speaker_boost=use_speaker_boost,
        speed=speed,
    )


def _extension_for_output_format(output_format: str) -> str:
    codec = output_format.split("_", 1)[0].lower()
    if codec in {"mp3", "wav", "pcm", "ulaw", "alaw", "opus"}:
        return codec
    return "mp3"


def _output_path(
    source_path: Path,
    output_dir: Path,
    output_format: str,
    part_index: Optional[int] = None,
    part_count: int = 1,
) -> Path:
    base_name = source_path.stem.replace("-OPTIMIZED", "")
    if part_count > 1 and part_index is not None:
        base_name = f"{base_name}_part{part_index:03d}"
    return output_dir / f"{base_name}.{_extension_for_output_format(output_format)}"


def split_text_for_model(
    text: str,
    model_id: str = DEFAULT_MODEL_ID,
    max_characters: Optional[int] = None,
) -> List[str]:
    """Split long text at natural boundaries while respecting the model limit."""
    limit = max_characters or MODEL_CHARACTER_LIMITS.get(model_id)
    if not limit or len(text) <= limit:
        return [text]

    if limit < 100:
        raise ValueError("max_characters must be at least 100 for long-form splitting")

    chunks: List[str] = []
    remaining = text.strip()

    # Prefer paragraph/sentence boundaries, then ordinary whitespace. If a single
    # token is longer than the limit, fall back to a hard split.
    boundary_patterns = [
        r"\n\s*\n",
        r"(?<=[.!?…])\s+",
        r"\s+",
    ]

    while len(remaining) > limit:
        window = remaining[: limit + 1]
        cut = -1

        for pattern in boundary_patterns:
            matches = list(re.finditer(pattern, window))
            if matches:
                candidate = matches[-1].end()
                # Avoid producing a tiny chunk just because a boundary occurs
                # near the beginning of the window.
                if candidate >= int(limit * 0.5):
                    cut = candidate
                    break

        if cut <= 0:
            cut = limit

        chunk = remaining[:cut].strip()
        if not chunk:
            chunk = remaining[:limit]
            cut = limit

        chunks.append(chunk)
        remaining = remaining[cut:].lstrip()

    if remaining:
        chunks.append(remaining)

    return chunks


def _write_audio(audio: Iterable[bytes], output_file: Path) -> int:
    bytes_written = 0
    with output_file.open("wb") as audio_file:
        for chunk in audio:
            if chunk:
                audio_file.write(chunk)
                bytes_written += len(chunk)

    if bytes_written == 0:
        output_file.unlink(missing_ok=True)
        raise RuntimeError(f"ElevenLabs returned no audio bytes for {output_file.name}")
    return bytes_written


def _rename_processed_source(source_path: Path) -> None:
    processed_path = source_path.parent / f"AUDIO_GENERATED-{source_path.name}"
    try:
        source_path.rename(processed_path)
    except OSError as exc:
        logger.warning("Could not rename processed source %s: %s", source_path.name, exc)


def _validate_text_length(text: str, model_id: str, max_characters: Optional[int]) -> None:
    character_limit = max_characters or MODEL_CHARACTER_LIMITS.get(model_id)
    if character_limit and len(text) > character_limit:
        raise ValueError(
            f"Text has {len(text)} characters, exceeding the configured "
            f"{character_limit}-character limit for {model_id}"
        )


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
    max_characters: Optional[int] = None,
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
        _validate_voice_settings(stability, similarity_boost, style, speed)

        source_path = Path(file_path)
        destination_dir = Path(output_dir)
        destination_dir.mkdir(parents=True, exist_ok=True)
        output_file = _output_path(source_path, destination_dir, output_format)

        text_content = source_path.read_text(encoding="utf-8")
        if not text_content.strip():
            return False, f"File {source_path.name} is empty"
        _validate_text_length(text_content, model_id, max_characters)

        logger.info(
            "Generating ElevenLabs audio: %s -> %s",
            source_path.name,
            output_file.name,
        )

        client = ElevenLabs(api_key=resolved_api_key)
        audio = client.text_to_speech.convert(
            voice_id=voice_id,
            text=text_content,
            model_id=model_id,
            output_format=output_format,
            voice_settings=_voice_settings(
                stability,
                similarity_boost,
                style,
                speed,
                use_speaker_boost,
            ),
        )
        bytes_written = _write_audio(audio, output_file)

        if rename_source:
            _rename_processed_source(source_path)

        logger.info("Generated %s (%d bytes)", output_file, bytes_written)
        return True, str(output_file)

    except Exception as exc:
        source_name = Path(file_path).name
        error_msg = f"Error processing {source_name}: {exc}"
        logger.error(error_msg)
        return False, error_msg


def process_markdown_files(
    file_paths,
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
    max_characters: Optional[int] = None,
    use_request_stitching: bool = True,
    skip_existing: bool = True,
    stop_on_error: bool = True,
    manifest_path=None,
) -> Dict:
    """
    Generate audiobook chunks sequentially with continuity between requests.

    Oversized Markdown files are split in memory at paragraph/sentence boundaries
    before calling the API. For models supporting request stitching, up to the
    three immediately preceding request IDs are supplied. On resume, existing
    audio parts are skipped and their text is used as continuity context.
    """
    if not ELEVENLABS_AVAILABLE:
        return {"success": False, "error": "ElevenLabs SDK is not installed", "items": []}

    resolved_api_key = api_key or os.getenv("ELEVENLABS_API_KEY")
    if not resolved_api_key:
        return {"success": False, "error": "ELEVENLABS_API_KEY is not configured", "items": []}

    try:
        _validate_voice_settings(stability, similarity_boost, style, speed)
    except ValueError as exc:
        return {"success": False, "error": str(exc), "items": []}

    sources = [Path(path) for path in file_paths]
    destination_dir = Path(output_dir)
    destination_dir.mkdir(parents=True, exist_ok=True)
    manifest = (
        Path(manifest_path)
        if manifest_path
        else destination_dir / "elevenlabs_generation_manifest.json"
    )

    client = ElevenLabs(api_key=resolved_api_key)
    settings = _voice_settings(
        stability,
        similarity_boost,
        style,
        speed,
        use_speaker_boost,
    )

    request_stitching_enabled = use_request_stitching and model_id != "eleven_v3"
    if use_request_stitching and not request_stitching_enabled:
        logger.warning("Request stitching is disabled for model %s", model_id)

    # Build all API-sized generation units first. This gives each request accurate
    # next_text context, even when one Markdown source becomes several audio parts.
    units: List[Dict] = []
    for source_path in sources:
        text_content = source_path.read_text(encoding="utf-8")
        if not text_content.strip():
            units.append(
                {
                    "source_path": source_path,
                    "text": "",
                    "part_index": 1,
                    "part_count": 1,
                }
            )
            continue

        parts = split_text_for_model(text_content, model_id, max_characters)
        for part_index, part_text in enumerate(parts, 1):
            units.append(
                {
                    "source_path": source_path,
                    "text": part_text,
                    "part_index": part_index,
                    "part_count": len(parts),
                }
            )

    items: List[Dict] = []
    previous_request_ids: List[str] = []
    previous_text: Optional[str] = None
    generated = skipped = failed = 0
    source_failed: Dict[Path, bool] = {source: False for source in sources}

    for index, unit in enumerate(units):
        source_path = unit["source_path"]
        text_content = unit["text"]
        part_index = unit["part_index"]
        part_count = unit["part_count"]
        output_file = _output_path(
            source_path,
            destination_dir,
            output_format,
            part_index=part_index,
            part_count=part_count,
        )

        entry: Dict = {
            "source": str(source_path),
            "part": part_index,
            "parts": part_count,
            "output": str(output_file),
            "characters": len(text_content),
            "model_id": model_id,
            "voice_id": voice_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

        try:
            if not text_content.strip():
                raise ValueError(f"File {source_path.name} is empty")

            next_text = None
            if index + 1 < len(units):
                candidate = units[index + 1]["text"]
                next_text = candidate if candidate.strip() else None

            if skip_existing and output_file.exists() and output_file.stat().st_size > 0:
                entry["status"] = "skipped_existing"
                entry["bytes"] = output_file.stat().st_size
                items.append(entry)
                skipped += 1
                previous_request_ids.clear()
                previous_text = text_content
            else:
                request_kwargs = {
                    "voice_id": voice_id,
                    "text": text_content,
                    "model_id": model_id,
                    "output_format": output_format,
                    "voice_settings": settings,
                }
                if next_text:
                    request_kwargs["next_text"] = next_text

                if request_stitching_enabled and previous_request_ids:
                    request_kwargs["previous_request_ids"] = previous_request_ids[-3:]
                elif previous_text:
                    request_kwargs["previous_text"] = previous_text

                logger.info(
                    "Generating ElevenLabs audiobook unit %d/%d: %s (%d/%d)",
                    index + 1,
                    len(units),
                    source_path.name,
                    part_index,
                    part_count,
                )

                with client.text_to_speech.with_raw_response.convert(**request_kwargs) as response:
                    bytes_written = _write_audio(response.data, output_file)
                    request_id = response.headers.get("request-id")
                    character_cost = response.headers.get("character-cost")

                entry.update(
                    {
                        "status": "generated",
                        "bytes": bytes_written,
                        "request_id": request_id,
                        "character_cost": character_cost,
                    }
                )
                items.append(entry)
                generated += 1

                if request_stitching_enabled and request_id:
                    previous_request_ids.append(request_id)
                    previous_request_ids = previous_request_ids[-3:]
                else:
                    previous_request_ids.clear()

                previous_text = text_content

            is_last_part_for_source = part_index == part_count
            if (
                rename_source
                and is_last_part_for_source
                and not source_failed[source_path]
                and source_path.exists()
            ):
                _rename_processed_source(source_path)

        except Exception as exc:
            failed += 1
            source_failed[source_path] = True
            entry.update({"status": "failed", "error": str(exc)})
            items.append(entry)
            logger.error(
                "Failed audiobook unit %s (%d/%d): %s",
                source_path.name,
                part_index,
                part_count,
                exc,
            )
            previous_request_ids.clear()
            previous_text = None
            if stop_on_error:
                break

    result = {
        "success": failed == 0,
        "source_files": len(sources),
        "generation_units": len(units),
        "generated": generated,
        "skipped": skipped,
        "failed": failed,
        "items": items,
        "manifest_path": str(manifest),
    }
    manifest.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return result

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
