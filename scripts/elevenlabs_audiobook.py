#!/usr/bin/env python3
"""Preflight or generate the remaining ElevenLabs audiobook chunks."""

import argparse
import json
import sys
from pathlib import Path

import yaml

from audio_chunk_generator import (
    DEFAULT_MODEL_ID,
    MODEL_CHARACTER_LIMITS,
    process_markdown_files,
    split_text_for_model,
)


def pending_sources(input_dir: Path, chapter: str | None = None, limit_files: int = 0):
    files = sorted(
        path
        for path in input_dir.glob("*.md")
        if not path.name.startswith(("AUDIO_GENERATED-", "ESPEAK_AUDIO-"))
    )
    if chapter:
        prefix = f"chapter_{str(chapter).zfill(2)}"
        files = [path for path in files if path.name.startswith(prefix)]
    if limit_files > 0:
        files = files[:limit_files]
    return files


def load_elevenlabs_config(config_path: Path) -> dict:
    data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    return dict(data.get("tts", {}).get("elevenlabs", {}))


def build_preflight(files, model_id: str, max_characters: int | None):
    source_details = []
    total_characters = 0
    total_units = 0

    for path in files:
        text = path.read_text(encoding="utf-8")
        parts = split_text_for_model(text, model_id, max_characters)
        characters = len(text)
        total_characters += characters
        total_units += len(parts)
        source_details.append(
            {
                "source": str(path),
                "characters": characters,
                "generation_units": len(parts),
                "largest_unit": max((len(part) for part in parts), default=0),
            }
        )

    return {
        "model_id": model_id,
        "model_character_limit": max_characters
        or MODEL_CHARACTER_LIMITS.get(model_id),
        "source_files": len(files),
        "total_characters": total_characters,
        "generation_units": total_units,
        "sources": source_details,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Preflight or generate the remaining ElevenLabs audiobook chunks"
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config.yaml"),
        help="Project YAML configuration",
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path("data/4-markdown-chunks-optimized"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/5-audio-chunks"),
    )
    parser.add_argument(
        "--preflight",
        action="store_true",
        help="Report the generation plan without calling ElevenLabs",
    )
    parser.add_argument(
        "--chapter",
        help="Restrict processing to a chapter number, e.g. 35",
    )
    parser.add_argument(
        "--limit-files",
        type=int,
        default=0,
        help="Process at most this many source files (0 means all)",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("elevenlabs_preflight.json"),
        help="Where to write the JSON preflight report",
    )
    args = parser.parse_args()

    settings = load_elevenlabs_config(args.config)
    model_id = settings.get("model_id", DEFAULT_MODEL_ID)
    max_characters = settings.get("max_characters")
    files = pending_sources(args.input_dir, args.chapter, args.limit_files)

    report = build_preflight(files, model_id, max_characters)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(
        f"Preflight: {report['source_files']} source files, "
        f"{report['generation_units']} API-sized units, "
        f"{report['total_characters']} source characters."
    )
    print(f"Report: {args.report}")

    if args.preflight:
        return 0

    if not files:
        print("No pending Markdown files selected.")
        return 0

    result = process_markdown_files(
        file_paths=files,
        output_dir=args.output_dir,
        **settings,
    )
    print(
        f"Generation: {result.get('generated', 0)} generated, "
        f"{result.get('skipped', 0)} skipped, "
        f"{result.get('failed', 0)} failed."
    )
    print(f"Manifest: {result.get('manifest_path', 'n/a')}")
    return 0 if result.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
