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
  python main.py --stage all             # Run the entire pipeline
"""

import os
import sys
import argparse
import logging
from pathlib import Path

# Import processing modules
from pdf_extractor import PDFProcessor
from chunker_splitter import MarkdownChunker
from text_optimizer import BatchProcessor
from audio_chunk_generator import process_markdown_file
from audio_concatenator import process_all_chapters

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('lidske_jednani_processing.log')
    ]
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
for directory in [PDF_DIR, MARKDOWN_DIR, CHUNKS_DIR, OPTIMIZED_DIR, AUDIO_CHUNKS_DIR, AUDIO_CHAPTERS_DIR]:
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

def optimize_text_stage():
    """Optimize markdown chunks for text-to-speech."""
    logger.info("Starting text optimization stage")
    
    # Check for Anthropic API key
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        logger.error("Anthropic API key not found. Please set the ANTHROPIC_API_KEY environment variable.")
        sys.exit(1)
    
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
    
    # Initialize the batch processor
    processor = BatchProcessor(
        api_key=api_key,
        base_dir=str(CHUNKS_DIR)
    )
    
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
    """Generate audio from optimized markdown chunks."""
    logger.info("Starting audio generation stage")
    
    # Check for ElevenLabs API key
    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        logger.error("ElevenLabs API key not found. Please set the ELEVENLABS_API_KEY environment variable.")
        sys.exit(1)
    
    # Get all optimized markdown files that haven't been processed yet
    optimized_files = []
    for file in OPTIMIZED_DIR.glob("*.md"):
        # Skip files that have already been processed
        if file.name.startswith("AUDIO_GENERATED-"):
            continue
        optimized_files.append(file)
    
    if not optimized_files:
        logger.warning("No unprocessed optimized markdown files found")
        return
    
    # Process each file
    for file in optimized_files:
        logger.info(f"Processing {file.name}")
        success, result = process_markdown_file(
            file_path=file,
            output_dir=AUDIO_CHUNKS_DIR,
            voice_id="OJtLHqR5g0hxcgc27j7C",  # Czech voice ID
            model_id="eleven_multilingual_v2",
            stability=0.5,
            similarity_boost=0.75,
            style=0.0
        )
        
        if not success:
            logger.error(f"Failed to process {file.name}: {result}")
    
    logger.info("Audio generation completed")

def concatenate_audio_stage():
    """Concatenate audio chunks into full chapters."""
    logger.info("Starting audio concatenation stage")
    process_all_chapters(AUDIO_CHUNKS_DIR, AUDIO_CHAPTERS_DIR)
    logger.info("Audio concatenation completed")

def main():
    """Main function to orchestrate the processing pipeline."""
    parser = argparse.ArgumentParser(
        description='Lidské Jednání Project - Processing Pipeline',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        '--stage',
        type=str,
        choices=['pdf-extract', 'chunk', 'optimize', 'audio-gen', 'concat', 'all'],
        default='all',
        help='Processing stage to run'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Set logging level based on verbosity
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    try:
        # Run the specified stage or all stages
        if args.stage == 'pdf-extract' or args.stage == 'all':
            extract_pdf_stage()
        
        if args.stage == 'chunk' or args.stage == 'all':
            chunk_markdown_stage()
        
        if args.stage == 'optimize' or args.stage == 'all':
            optimize_text_stage()
        
        if args.stage == 'audio-gen' or args.stage == 'all':
            generate_audio_stage()
        
        if args.stage == 'concat' or args.stage == 'all':
            concatenate_audio_stage()
        
        logger.info(f"Pipeline stage '{args.stage}' completed successfully")
    
    except Exception as e:
        logger.error(f"Error in pipeline: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
