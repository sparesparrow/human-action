#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script to separate paragraphs into individual files and generate audio for each
"""

import os
import re
import sys
import logging
import subprocess
from pathlib import Path
from tqdm import tqdm

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('paragraph_separation.log')
    ]
)
logger = logging.getLogger(__name__)

# Constants
FFMPEG_QUALITY = "2"
INPUT_DIR = Path("data/4-markdown-chunks-optimized")
OUTPUT_DIR = Path("data/7-paragraphs")
AUDIO_OUTPUT_DIR = OUTPUT_DIR / "audio"
TEXT_OUTPUT_DIR = OUTPUT_DIR / "text"

def clean_filename(text):
    """Create a safe filename from text."""
    # Take first 50 characters of text, replace unsafe chars
    safe_text = re.sub(r'[^a-zA-Z0-9\s-]', '', text[:50]).strip()
    safe_text = re.sub(r'\s+', '-', safe_text)
    return safe_text

def split_into_paragraphs(text):
    """Split text into paragraphs, handling various newline formats."""
    # Split on double newlines or more
    paragraphs = re.split(r'\n\s*\n', text)
    # Filter out empty paragraphs and strip whitespace
    return [p.strip() for p in paragraphs if p.strip()]

def generate_audio(text, output_file, voice="cs", rate=175, pitch=50, volume=100):
    """Generate audio for a paragraph using espeak-ng."""
    try:
        # Save text to a temporary file
        temp_text_file = output_file.parent / f"temp_{output_file.stem}.txt"
        temp_wav_file = output_file.parent / f"temp_{output_file.stem}.wav"
        
        with open(temp_text_file, 'w', encoding='utf-8') as f:
            f.write(text)
        
        # Generate WAV using espeak-ng
        espeak_cmd = [
            'espeak-ng',
            '-v', voice,
            '-s', str(rate),
            '-p', str(pitch),
            '-a', str(volume),
            '-f', str(temp_text_file),
            '-w', str(temp_wav_file)
        ]
        subprocess.run(espeak_cmd, check=True, capture_output=True)
        
        # Convert to MP3 using ffmpeg
        ffmpeg_cmd = [
            'ffmpeg', '-y',
            '-i', str(temp_wav_file),
            '-codec:a', 'libmp3lame',
            '-qscale:a', FFMPEG_QUALITY,
            str(output_file)
        ]
        subprocess.run(ffmpeg_cmd, check=True, capture_output=True)
        
        # Cleanup temporary files
        temp_text_file.unlink()
        temp_wav_file.unlink()
        
        return True
    except Exception as e:
        logger.error(f"Error generating audio: {e}")
        return False

def process_file(file_path):
    """Process a single markdown file, splitting it into paragraphs and generating audio."""
    try:
        # Read the file
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Get chapter number for organization
        chapter_match = re.search(r'chapter_(\d+)', file_path.stem)
        chapter_num = chapter_match.group(1) if chapter_match else "unknown"
        
        # Create chapter-specific directories
        chapter_text_dir = TEXT_OUTPUT_DIR / f"chapter_{chapter_num}"
        chapter_audio_dir = AUDIO_OUTPUT_DIR / f"chapter_{chapter_num}"
        chapter_text_dir.mkdir(parents=True, exist_ok=True)
        chapter_audio_dir.mkdir(parents=True, exist_ok=True)
        
        # Split into paragraphs
        paragraphs = split_into_paragraphs(content)
        
        # Process each paragraph
        for i, paragraph in enumerate(paragraphs, 1):
            # Create a base name for the files
            base_name = f"para_{i:03d}-{clean_filename(paragraph)}"
            
            # Save text file
            text_file = chapter_text_dir / f"{base_name}.md"
            with open(text_file, 'w', encoding='utf-8') as f:
                f.write(paragraph)
            
            # Generate audio file
            audio_file = chapter_audio_dir / f"{base_name}.mp3"
            if not audio_file.exists():
                success = generate_audio(paragraph, audio_file)
                if success:
                    logger.info(f"Generated audio for {audio_file.name}")
                else:
                    logger.error(f"Failed to generate audio for {audio_file.name}")
            else:
                logger.info(f"Audio file already exists: {audio_file.name}")
        
        return True
    except Exception as e:
        logger.error(f"Error processing file {file_path}: {e}")
        return False

def main():
    """Main function to process all markdown files."""
    # Create output directories
    TEXT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    AUDIO_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Get list of markdown files
    markdown_files = list(INPUT_DIR.glob('*-OPTIMIZED.md'))
    logger.info(f"Found {len(markdown_files)} files to process")
    
    # Process each file
    success_count = 0
    for file_path in tqdm(markdown_files, desc="Processing files"):
        if process_file(file_path):
            success_count += 1
    
    logger.info(f"Processing complete. Successfully processed {success_count}/{len(markdown_files)} files")

if __name__ == "__main__":
    main() 