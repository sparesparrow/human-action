#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Lidské Jednání Project - Main Orchestration Script
--------------------------------------------------

This script coordinates the entire processing pipeline for the project:
1. PDF to Markdown extraction
2. Markdown chunking
3. Text optimization
4. Audio generation
5. Audio concatenation

Usage:
  python main.py --stage pdf-extract     # Extract text from PDFs
  python main.py --stage chunk           # Split markdown into chunks
  python main.py --stage optimize        # Optimize text for TTS
  python main.py --stage audio-gen       # Generate audio for chunks
  python main.py --stage concat          # Concatenate audio files
  python main.py --stage voice-variants  # Generate voice variants for comparison
  python main.py --stage all             # Run the entire pipeline
"""

import argparse
import logging
import os
import sys
from pathlib import Path

# Unified TTS engine detection with priority order: Piper > Coqui > espeak > Mock
import shutil

def detect_available_tts_engines():
    """Detect available TTS engines in priority order."""
    engines_status = {
        'piper': False,
        'coqui': False,
        'espeak': False,
        'elevenlabs': False
    }

    # 1. Check Piper (highest priority)
    try:
        from piper_audio_chunk_generator import PiperAudioChunkGenerator
        # Check if piper binary is available
        piper_binary = PiperAudioChunkGenerator._find_piper_binary()
        engines_status['piper'] = piper_binary is not None
    except (ImportError, Exception):
        engines_status['piper'] = False

    # 2. Check Coqui TTS
    try:
        import TTS
        engines_status['coqui'] = True
    except ImportError:
        engines_status['coqui'] = False

    # 3. Check espeak/espeak-ng
    engines_status['espeak'] = bool(shutil.which('espeak') or shutil.which('espeak-ng'))

    # 4. Check ElevenLabs (lowest priority, as it's paid)
    try:
        from audio_chunk_generator import process_markdown_file
        engines_status['elevenlabs'] = True
    except (ImportError, SystemExit):
        engines_status['elevenlabs'] = False

    return engines_status

def setup_tts_engine(engines_status):
    """Set up the best available TTS engine based on priority."""
    global AUDIO_GENERATOR_TYPE, process_markdown_file

    # Priority order: Piper > Coqui > espeak > ElevenLabs > Mock
    priority_engines = ['piper', 'coqui', 'espeak', 'elevenlabs']

    for engine in priority_engines:
        if engines_status[engine]:
            AUDIO_GENERATOR_TYPE = engine

            if engine == 'piper':
                from piper_audio_chunk_generator import process_markdown_file
                print(f"✓ Using Piper TTS (fast, local, high quality)")
            elif engine == 'coqui':
                from coqui_audio_chunk_generator import process_markdown_file
                print(f"✓ Using Coqui TTS (high quality, multilingual)")
            elif engine == 'espeak':
                from espeak_audio_chunk_generator import EspeakAudioChunkGenerator
                def process_markdown_file(file_path, output_dir, **kwargs):
                    """Wrapper function to use espeak generator"""
                    generator = EspeakAudioChunkGenerator(
                        input_dir=str(Path(file_path).parent),
                        output_dir=str(output_dir)
                    )
                    result = generator.process()
                    return True, "Generated with espeak" if result else "Failed with espeak"
                print(f"✓ Using eSpeak-ng TTS (system binary)")
            elif engine == 'elevenlabs':
                from audio_chunk_generator import process_markdown_file
                print(f"⚠ Using ElevenLabs TTS (paid API - consider free alternatives)")

            return

    # No real engines available, use mock
    AUDIO_GENERATOR_TYPE = "mock"
    def process_markdown_file(file_path, output_dir, **kwargs):
        """Mock audio generation - just log that it would generate audio"""
        logger.info(f"Mock audio generation: {Path(file_path).name} -> {output_dir}")
        return True, "Mock audio generation (no TTS engine available)"

    print("⚠ No TTS engines available - using mock mode")
    print("Install free TTS engines:")
    print("  - Piper: https://github.com/rhasspy/piper")
    print("  - Coqui TTS: pip install TTS")
    print("  - eSpeak-ng: sudo apt install espeak-ng")

# Detect and setup TTS engine
engines_status = detect_available_tts_engines()
setup_tts_engine(engines_status)

from audio_concatenator import process_all_chapters
from chunker_splitter import MarkdownChunker

# Import processing modules
from pdf_extractor import PDFProcessor
from text_optimizer import BatchProcessor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("lidske_jednani_processing.log"),
    ],
)
logger = logging.getLogger(__name__)

# Project directory structure
PROJECT_ROOT = Path(__file__).parent
DATA_DIR = PROJECT_ROOT / "data"
PDF_DIR = DATA_DIR / "1-pdf"
MARKDOWN_DIR = DATA_DIR / "2-markdown-chapters"
CHUNKS_DIR = DATA_DIR / "3-markdown-chunks"
OPTIMIZED_DIR = DATA_DIR / "4-markdown-chunks-optimized"
AUDIO_CHUNKS_DIR = DATA_DIR / "5-audio-chunks"
AUDIO_CHAPTERS_DIR = DATA_DIR / "6-audio-chapters"

# Ensure all directories exist
for directory in [
    PDF_DIR,
    MARKDOWN_DIR,
    CHUNKS_DIR,
    OPTIMIZED_DIR,
    AUDIO_CHUNKS_DIR,
    AUDIO_CHAPTERS_DIR,
]:
    directory.mkdir(parents=True, exist_ok=True)


def extract_pdf_stage():
    """Extract text from PDF files to markdown chapters."""
    logger.info("Starting PDF extraction stage")
    processor = PDFProcessor(str(PDF_DIR), str(MARKDOWN_DIR))
    processor.process()
    logger.info("PDF extraction completed")


def chunk_markdown_stage():
    """Split markdown chapters into smaller chunks."""
    logger.info("Starting markdown chunking stage")
    chunker = MarkdownChunker(str(MARKDOWN_DIR), str(CHUNKS_DIR))
    chunker.process_all()
    logger.info("Markdown chunking completed")


def optimize_text_stage(skip_if_done=True):
    """Optimize markdown chunks for text-to-speech."""
    logger.info("Starting text optimization stage")

    # Check if already optimized
    if skip_if_done:
        existing = list(OPTIMIZED_DIR.glob("*-OPTIMIZED.md"))
        if existing:
            logger.info(f"Found {len(existing)} optimized files, skipping API calls")
            return

    # Skip Anthropic optimization (paid API) - use existing optimized files or skip
    logger.info("Skipping Anthropic text optimization (paid API). Using existing optimized files or raw chunks.")
    logger.info("Note: Text optimization improves TTS quality but is optional. Existing optimized files will be used.")
    return

    # Get all markdown chunk files that haven't been optimized yet
    chunk_files = []
    for file in CHUNKS_DIR.glob("*.md"):
        # Skip files that have already been processed
        if file.stem.endswith("-OPTIMIZED"):
            continue
        chunk_files.append(file.name)

    if not chunk_files:
        logger.warning("No unprocessed markdown chunks found")
        return

    # Initialize the batch processor with skip_api=False since we have API key
    processor = BatchProcessor(api_key=api_key, base_dir=str(CHUNKS_DIR), skip_api=False)

    # Process in batches if there are many files
    # For simplicity, we'll just pass all files here
    # In a real implementation, you might want to process in smaller batches
    import asyncio

    asyncio.run(processor.process_files(chunk_files))

    # Move optimized files to the optimized directory
    for file in CHUNKS_DIR.glob("*-OPTIMIZED.md"):
        dest_file = OPTIMIZED_DIR / file.name
        file.rename(dest_file)

    logger.info("Text optimization completed")


def generate_audio_stage():
    """Generate audio from optimized markdown chunks using available free TTS engines."""
    logger.info("Starting audio generation stage")
    logger.info(f"Using TTS engine: {AUDIO_GENERATOR_TYPE}")

    # Get all optimized markdown files that haven't been processed yet
    optimized_files = []
    for file in OPTIMIZED_DIR.glob("*.md"):
        # Skip files that have already been processed
        if file.name.startswith("AUDIO_GENERATED-") or file.name.startswith("ESPEAK_AUDIO-"):
            continue
        optimized_files.append(file)

    if not optimized_files:
        logger.warning("No unprocessed optimized markdown files found")
        return

    logger.info(f"Found {len(optimized_files)} files to process")

    # Process each file using the detected TTS engine
    processed_count = 0
    failed_count = 0
    
    for file in optimized_files:
        logger.info(f"Processing {file.name} ({processed_count + 1}/{len(optimized_files)})")
        try:
            success, result = process_markdown_file(
                file_path=file,
                output_dir=AUDIO_CHUNKS_DIR,
            )

            if success:
                processed_count += 1
                logger.info(f"✓ Successfully processed {file.name}")
            else:
                failed_count += 1
                logger.warning(f"⚠ Failed to process {file.name}: {result}")
        except Exception as e:
            failed_count += 1
            logger.error(f"✗ Error processing {file.name}: {e}")

    logger.info(f"Audio generation completed: {processed_count} succeeded, {failed_count} failed")


def concatenate_audio_stage():
    """Concatenate audio chunks into full chapters."""
    logger.info("Starting audio concatenation stage")
    process_all_chapters(AUDIO_CHUNKS_DIR, AUDIO_CHAPTERS_DIR)
    logger.info("Audio concatenation completed")


def generate_voice_variants_stage():
    """Generate voice variants for comparison."""
    logger.info("Starting voice variants generation stage")

    try:
        from scripts.generate_voice_variants import VoiceVariantGenerator

        generator = VoiceVariantGenerator()

        # Get available optimized chapters
        optimized_dir = Path("data/4-markdown-chunks-optimized")
        if not optimized_dir.exists():
            logger.warning("Optimized chunks directory not found")
            return

        # Generate variants for all available chapters
        chapter_files = list(optimized_dir.glob("*.md"))
        if not chapter_files:
            logger.warning("No optimized markdown files found")
            return

        logger.info(f"Found {len(chapter_files)} chapters to process")

        for chapter_file in chapter_files:
            chapter_name = chapter_file.stem.replace("-OPTIMIZED", "")
            logger.info(f"Generating variants for {chapter_name}")

            try:
                results = generator.generate_variants(str(chapter_file), mode="all")
                if results and results.get('variants'):
                    successful = len([v for v in results['variants'] if v.get('success')])
                    logger.info(f"Generated {successful} variants for {chapter_name}")
                else:
                    logger.warning(f"No variants generated for {chapter_name}")
            except Exception as e:
                logger.error(f"Failed to generate variants for {chapter_name}: {e}")

        logger.info("Voice variants generation completed")

    except ImportError as e:
        logger.error(f"Voice variant generation not available: {e}")
        logger.info("Install required dependencies or run scripts manually")


def main():
    """Main function to orchestrate the processing pipeline."""
    parser = argparse.ArgumentParser(
        description="Lidské Jednání Project - Processing Pipeline",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "--stage",
        type=str,
        choices=["pdf-extract", "chunk", "optimize", "audio-gen", "concat", "voice-variants", "all"],
        default="all",
        help="Processing stage to run",
    )

    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    # Set logging level based on verbosity
    if args.verbose:
        logger.setLevel(logging.DEBUG)

    try:
        # Run the specified stage or all stages
        if args.stage == "pdf-extract" or args.stage == "all":
            extract_pdf_stage()

        if args.stage == "chunk" or args.stage == "all":
            chunk_markdown_stage()

        if args.stage == "optimize" or args.stage == "all":
            optimize_text_stage()

        if args.stage == "audio-gen" or args.stage == "all":
            generate_audio_stage()

        if args.stage == "concat" or args.stage == "all":
            concatenate_audio_stage()

        if args.stage == "voice-variants" or args.stage == "all":
            generate_voice_variants_stage()

        logger.info(f"Pipeline stage '{args.stage}' completed successfully")

    except Exception as e:
        logger.error(f"Error in pipeline: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
