#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Audio Concatenation Tool
------------------------

A module for concatenating audio files from individual chunks into complete chapters.
This script uses ffmpeg to merge multiple MP3 files into a single audio file.
"""

import os
import sys
import logging
import argparse
import re
import subprocess
from pathlib import Path
from typing import List, Optional, Dict

# Nastavení loggování
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def natural_sort_key(s: str) -> List:
    """Helper function for natural sorting of filenames."""
    # Converts "chapter_1a" to ["chapter_", 1, "a"] for natural sorting
    return [int(c) if c.isdigit() else c.lower() for c in re.split(r'(\d+)', s)]

def get_chapter_number(filename: str) -> str:
    """Extract chapter number from filename (e.g., 'chapter_01a.mp3' -> '01')."""
    match = re.search(r'chapter_(\d+)', filename)
    if match:
        return match.group(1)
    return None

def group_files_by_chapter(files: List[Path]) -> Dict[str, List[Path]]:
    """Group files by their chapter number."""
    chapters = {}
    for file in files:
        chapter_num = get_chapter_number(file.name)
        if chapter_num:
            if chapter_num not in chapters:
                chapters[chapter_num] = []
            chapters[chapter_num].append(file)
    
    # Sort files within each chapter
    for chapter_num in chapters:
        chapters[chapter_num].sort(key=lambda p: natural_sort_key(p.name))
    
    return chapters

class AudioConcatenator:
    """
    Class that handles concatenation of audio files.
    Provides a convenient interface for the existing functions.
    """
    
    def __init__(self, input_dir: str, output_dir: str):
        """
        Initialize the audio concatenator.
        
        Args:
            input_dir: Directory containing audio chunks
            output_dir: Directory to save concatenated audio files
        """
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        
        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def concatenate_audio_files(self, audio_files: List[Path], output_file: Path) -> Path:
        """
        Concatenate multiple audio files using ffmpeg.
        
        Args:
            audio_files: List of audio files to concatenate
            output_file: Path to save the concatenated file
            
        Returns:
            Path to the concatenated file
        """
        # Call the module function
        success = concatenate_audio_files(audio_files, output_file)
        
        if not success:
            raise RuntimeError("Failed to concatenate audio files")
            
        return output_file
    
    def process(self, output_filename: str = "audiobook.mp3") -> Path:
        """
        Process all audio chunks in the input directory.
        
        Args:
            output_filename: Name of the output audiobook file
            
        Returns:
            Path to the concatenated audiobook
        """
        # Get all MP3 files in input directory
        mp3_files = sorted(self.input_dir.glob("*.mp3"), key=lambda p: natural_sort_key(p.name))
        
        if not mp3_files:
            raise FileNotFoundError(f"No MP3 files found in {self.input_dir}")
        
        # Concatenate all audio files into a single file
        output_file = self.output_dir / output_filename
        return self.concatenate_audio_files(mp3_files, output_file)

def concatenate_audio_files(input_files: List[Path], output_file: Path) -> bool:
    """
    Concatenate multiple audio files using ffmpeg.
    
    Args:
        input_files: List of audio files to concatenate
        output_file: Path to save the concatenated file
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Ensure output directory exists
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Create a temporary file listing all input files
        file_list_path = output_file.parent / f"filelist_{output_file.stem}.txt"
        with open(file_list_path, 'w', encoding='utf-8') as f:
            for input_file in input_files:
                f.write(f"file '{input_file.absolute()}'\n")
        
        # Run ffmpeg to concatenate the files
        cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", str(file_list_path),
            "-c", "copy",
            str(output_file)
        ]
        
        logger.info(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # Remove temporary file
        file_list_path.unlink()
        
        if result.returncode != 0:
            logger.error(f"Error concatenating audio files: {result.stderr}")
            return False
        
        logger.info(f"Successfully concatenated {len(input_files)} files into {output_file}")
        return True
    
    except Exception as e:
        logger.error(f"Error during audio concatenation: {str(e)}")
        return False

def process_chapter(chapter_num: str, files: List[Path], output_dir: Path) -> Optional[Path]:
    """
    Process a single chapter by concatenating its audio files.
    
    Args:
        chapter_num: Chapter number
        files: List of audio files for this chapter
        output_dir: Directory to save the output file
        
    Returns:
        Path to the output file or None if failed
    """
    if not files:
        logger.warning(f"No files found for chapter {chapter_num}")
        return None
    
    # Format chapter number with leading zeros if needed
    chapter_num_formatted = chapter_num.zfill(2)
    output_file = output_dir / f"{chapter_num_formatted}-Jednající_člověk.mp3"
    
    # Get chapter title if available (customize this based on your naming convention)
    # This is just a placeholder - you might want to use a mapping of chapter numbers to titles
    chapter_titles = {
        "01": "Jednající_člověk",
        "02": "Epistemologické_problémy_vědy_o_lidském_jednání",
        "03": "Revolta_Proti_Rozumu"
        # Add more chapter titles as needed
    }
    
    chapter_title = chapter_titles.get(chapter_num_formatted, f"Chapter_{chapter_num_formatted}")
    output_file = output_dir / f"{chapter_num_formatted}-{chapter_title}.mp3"
    
    logger.info(f"Processing chapter {chapter_num_formatted}: {chapter_title}")
    logger.info(f"Concatenating {len(files)} files: {[f.name for f in files]}")
    
    success = concatenate_audio_files(files, output_file)
    return output_file if success else None

def process_all_chapters(input_dir: Path, output_dir: Path) -> int:
    """
    Process all chapters by concatenating audio files.
    
    Args:
        input_dir: Directory containing audio chunks
        output_dir: Directory to save concatenated chapter files
        
    Returns:
        Number of successfully processed chapters
    """
    # Ensure directories exist
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Get all MP3 files
    mp3_files = sorted(input_dir.glob("*.mp3"), key=lambda p: natural_sort_key(p.name))
    
    if not mp3_files:
        logger.warning(f"No MP3 files found in {input_dir}")
        return 0
    
    # Group files by chapter
    chapters = group_files_by_chapter(mp3_files)
    
    if not chapters:
        logger.warning("Could not identify any chapters from the filenames")
        return 0
    
    # Process each chapter
    successful_chapters = 0
    for chapter_num in sorted(chapters.keys(), key=int):
        result = process_chapter(chapter_num, chapters[chapter_num], output_dir)
        if result:
            successful_chapters += 1
    
    logger.info(f"Processed {successful_chapters} out of {len(chapters)} chapters successfully")
    return successful_chapters

def main():
    """Main entry point for command-line use."""
    parser = argparse.ArgumentParser(
        description='Audio Concatenation Tool',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        '-i', '--input-dir',
        type=str,
        default="./data/5-audio-chunks-espeak",
        help='Input directory containing audio chunks'
    )
    
    parser.add_argument(
        '-o', '--output-dir',
        type=str,
        default="./data/6-audio-chapters",
        help='Output directory for concatenated chapters'
    )
    
    parser.add_argument(
        '-c', '--chapter',
        type=str,
        help='Process only a specific chapter number (e.g., "01")'
    )
    
    args = parser.parse_args()
    
    # Check for ffmpeg
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
    except (subprocess.SubprocessError, FileNotFoundError):
        logger.error("ffmpeg is not installed or not in PATH. Please install ffmpeg.")
        sys.exit(1)
    
    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    
    if args.chapter:
        # Process a single chapter
        mp3_files = sorted(input_dir.glob(f"chapter_{args.chapter}*.mp3"), key=lambda p: natural_sort_key(p.name))
        if not mp3_files:
            logger.error(f"No MP3 files found for chapter {args.chapter}")
            sys.exit(1)
        
        result = process_chapter(args.chapter, mp3_files, output_dir)
        if result:
            logger.info(f"Successfully processed chapter {args.chapter}")
            sys.exit(0)
        else:
            logger.error(f"Failed to process chapter {args.chapter}")
            sys.exit(1)
    else:
        # Process all chapters
        num_processed = process_all_chapters(input_dir, output_dir)
        if num_processed > 0:
            logger.info(f"Successfully processed {num_processed} chapters")
            sys.exit(0)
        else:
            logger.error("No chapters were processed successfully")
            sys.exit(1)

if __name__ == "__main__":
    main() 