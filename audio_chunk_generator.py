#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Modern ElevenLabs Text-to-Speech Processor
------------------------------------------

A script for converting markdown files to audio using the latest ElevenLabs API.
This script will generate an audio file from a markdown file and rename the processed
file by prefixing it with "AUDIO_GENERATED-".
"""

import argparse
import logging
import os
import sys
import time
from pathlib import Path

# Import ElevenLabs SDK with the latest structure
try:
    from elevenlabs import play, save
    from elevenlabs.client import ElevenLabs
    from elevenlabs import VoiceSettings
except ImportError:
    print("ElevenLabs SDK není nainstalován. Instalujte pomocí: pip install elevenlabs")
    sys.exit(1)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def process_markdown_file(
    file_path,
    output_dir,
    voice_id,
    model_id,
    stability=0.5,
    similarity_boost=0.75,
    style=0.0,
):
    """
    Process a single markdown file to generate audio using the latest ElevenLabs API.

    Args:
        file_path: Path to the markdown file
        output_dir: Directory to save the audio file
        voice_id: ElevenLabs voice ID
        model_id: ElevenLabs model ID
        stability: Voice stability setting (0.0-1.0)
        similarity_boost: Voice similarity boost setting (0.0-1.0)
        style: Voice style setting (0.0-1.0)

    Returns:
        Tuple (success, output_file_path)
    """
    try:
        # Create Path objects
        file_path = Path(
            file_path
        )  # i.e. data/4-markdown-chunks-optimized/chapter_30a-OPTIMIZED.md
        output_dir = Path(output_dir)  # data/5-audio-chunks

        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)

        # Get base name without -OPTIMIZED suffix
        base_name = file_path.stem.replace("-OPTIMIZED", "")  # i.e. chapter_30a.md
        output_file = output_dir / f"{base_name}.mp3"  # i.e. chapter_30a.mp3

        logger.info(f"Processing file: {file_path.name} -> {output_file.name}")

        # Read content from the markdown file
        with open(file_path, "r", encoding="utf-8") as f:
            text_content = f.read()

        if not text_content.strip():
            logger.warning(
                f"File {file_path.name} is empty or contains only whitespace"
            )
            return False, f"File {file_path.name} is empty"

        # Initialize the ElevenLabs client
        # The API key is automatically read from the ELEVENLABS_API_KEY environment variable
        client = ElevenLabs()

        # Generate audio using ElevenLabs API with the latest client structure
        logger.info(f"Generating audio for {file_path.name}...")

        audio = client.text_to_speech.convert(
            text=text_content,
            voice_id=voice_id,
            model_id=model_id,
            voice_settings=VoiceSettings(
                stability=stability,
                similarity_boost=similarity_boost,
                style=style,
                use_speaker_boost=True,
            ),
        )

        # Save the audio file
        save(audio, str(output_file))

        # Rename the processed markdown file by adding prefix
        new_name = file_path.parent / f"AUDIO_GENERATED-{file_path.name}"
        file_path.rename(new_name)

        logger.info(f"Successfully generated: {output_file}")
        logger.info(f"Renamed processed file to: {new_name.name}")

        return True, str(output_file)

    except Exception as e:
        error_msg = f"Error processing {file_path.name}: {str(e)}"
        logger.error(error_msg)
        return False, error_msg


def main():
    """Main entry point for command-line use."""
    parser = argparse.ArgumentParser(
        description="Modern ElevenLabs Text-to-Speech Processor",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument("file", type=str, help="Path to the markdown file to process")

    parser.add_argument(
        "-o",
        "--output-dir",
        type=str,
        default="./data/5-audio-chunks",
        help="Output directory for audio files",
    )

    parser.add_argument(
        "-v",
        "--voice-id",
        type=str,
        default="OJtLHqR5g0hxcgc27j7C",  # Czech voice from elevenlabs_text_to_speech.sh
        help="ID of the ElevenLabs voice to use",
    )

    parser.add_argument(
        "-m",
        "--model-id",
        type=str,
        default="eleven_multilingual_v2",  # Multilingual model
        help="ID of the ElevenLabs model to use",
    )

    parser.add_argument(
        "--stability", type=float, default=0.5, help="Voice stability (0.0-1.0)"
    )

    parser.add_argument(
        "--similarity-boost",
        type=float,
        default=0.75,
        help="Voice similarity boost (0.0-1.0)",
    )

    parser.add_argument(
        "--style", type=float, default=0.0, help="Voice style (0.0-1.0)"
    )

    parser.add_argument(
        "--api-key",
        type=str,
        help="ElevenLabs API key (defaults to ELEVENLABS_API_KEY environment variable)",
    )

    args = parser.parse_args()

    # Set API key if provided as argument
    if args.api_key:
        os.environ["ELEVENLABS_API_KEY"] = args.api_key

    # Check if API key is set
    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        logger.error(
            "ElevenLabs API key not provided. Use --api-key or set ELEVENLABS_API_KEY environment variable."
        )
        sys.exit(1)

    # Process the file
    success, result = process_markdown_file(
        args.file,
        args.output_dir,
        args.voice_id,
        args.model_id,
        args.stability,
        args.similarity_boost,
        args.style,
    )

    if success:
        logger.info("Processing completed successfully.")
        sys.exit(0)
    else:
        logger.error(f"Processing failed: {result}")
        sys.exit(1)


if __name__ == "__main__":
    main()
