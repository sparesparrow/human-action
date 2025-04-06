#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test script for audio_chunk_generator.py
"""

import logging
import os
import sys
from pathlib import Path

# Add parent directory to path so we can import the main script
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import the function from audio_chunk_generator.py
from audio_chunk_generator import process_markdown_file

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def main():
    """Run test for audio chunk generator"""
    # Configuration
    test_file = Path(__file__).parent / "test_tts_data.md"
    output_dir = Path(__file__).parent
    voice_id = "OJtLHqR5g0hxcgc27j7C"  # Czech voice
    model_id = "eleven_multilingual_v2"  # Multilingual model

    # Check if test file exists
    if not test_file.exists():
        logger.error(f"Test file not found: {test_file}")
        sys.exit(1)

    # Get API key from environment
    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        logger.error(
            "ElevenLabs API key not provided. Set ELEVENLABS_API_KEY environment variable."
        )
        sys.exit(1)

    # Set the API key as environment variable
    os.environ["ELEVENLABS_API_KEY"] = api_key

    logger.info(f"Testing audio generation with file: {test_file}")

    # Process the file
    success, result = process_markdown_file(
        test_file,
        output_dir,
        voice_id,
        model_id,
        stability=0.5,
        similarity_boost=0.75,
        style=0.0,
    )

    if success:
        logger.info(f"Test completed successfully. Audio file generated: {result}")
        sys.exit(0)
    else:
        logger.error(f"Test failed: {result}")
        sys.exit(1)


if __name__ == "__main__":
    main()
