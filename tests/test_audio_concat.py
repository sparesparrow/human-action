#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test script for audio_concat.py

This script demonstrates how to use the audio_concat.py module
to concatenate audio files for a specific chapter.
"""

import os
import subprocess
import sys
from pathlib import Path


def check_ffmpeg():
    """Check if ffmpeg is installed."""
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


def main():
    # Check if ffmpeg is installed
    if not check_ffmpeg():
        print("Error: ffmpeg is not installed or not in PATH")
        print("Please install ffmpeg before running this test")
        print("For example: sudo apt-get install ffmpeg")
        sys.exit(1)

    # Check if we have audio files to concatenate
    input_dir = Path("data/5-audio-chunks")
    if not input_dir.exists():
        print(f"Error: Input directory {input_dir} does not exist")
        sys.exit(1)

    # Check if we have files for chapter 30
    chapter_files = list(input_dir.glob("chapter_30*.mp3"))
    if not chapter_files:
        print(f"Error: No audio files found for chapter 30 in {input_dir}")
        print("Please run test_simple_tts.py first to generate some audio files")
        sys.exit(1)

    # Print the files we found
    print(f"Found {len(chapter_files)} audio files for chapter 30:")
    for file in sorted(chapter_files, key=lambda p: p.name):
        print(f"  - {file.name}")

    # Run the audio_concat.py script
    print("\nRunning audio_concat.py to concatenate chapter 30 files...")
    cmd = ["python", "audio_concat.py", "-c", "30"]
    print(f"Command: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)

        # Print the output
        print("\nCommand output:")
        print(result.stdout)

        if result.returncode != 0:
            print("Error:", result.stderr)
            sys.exit(1)

        # Check if the output file was created
        output_dir = Path("data/6-audio-chapters")
        output_file = output_dir / "30-Chapter_30.mp3"

        if output_file.exists():
            print(f"\nSuccess! Concatenated audio file created: {output_file}")
        else:
            print(f"\nError: Output file {output_file} was not created")
            sys.exit(1)

    except Exception as e:
        print(f"Error running audio_concat.py: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
