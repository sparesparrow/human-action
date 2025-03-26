#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script to organize audio files to match chapter structure
"""

import os
from pathlib import Path
import re
from pydub import AudioSegment

def get_chapter_number(filename):
    """Extract chapter number from filename."""
    match = re.search(r'chapter_(\d+)', filename)
    return int(match.group(1)) if match else None

def get_chapter_part(filename):
    """Extract chapter part (a, b, c, etc) from filename."""
    match = re.search(r'chapter_\d+([a-z])', filename)
    return match.group(1) if match else None

def combine_audio_files(input_dir, output_dir):
    """Combine audio files for each chapter."""
    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Group files by chapter number
    chapter_files = {}
    for file in input_dir.glob('*.mp3'):
        chapter_num = get_chapter_number(file.name)
        if chapter_num:
            if chapter_num not in chapter_files:
                chapter_files[chapter_num] = []
            chapter_files[chapter_num].append(file)
    
    # Sort files within each chapter by part
    for chapter_num in chapter_files:
        chapter_files[chapter_num].sort(key=lambda x: get_chapter_part(x.name) or '')
    
    # Process each chapter
    for chapter_num, files in sorted(chapter_files.items()):
        output_file = output_dir / f'chapter_{chapter_num}.mp3'
        print(f'Processing audio for chapter {chapter_num}...')
        
        # Skip if output file already exists
        if output_file.exists():
            print(f'Audio for chapter {chapter_num} already exists, skipping...')
            continue
        
        # Combine audio files
        if files:
            combined = AudioSegment.empty()
            for file in files:
                try:
                    audio = AudioSegment.from_mp3(str(file))
                    combined += audio
                except Exception as e:
                    print(f'Error processing {file}: {e}')
                    continue
            
            # Export combined audio
            if len(combined) > 0:
                try:
                    combined.export(str(output_file), format='mp3')
                    print(f'Created {output_file}')
                except Exception as e:
                    print(f'Error exporting {output_file}: {e}')

def main():
    # Define directories
    base_dir = Path('/home/sparrow/projects/human-action')
    audio_dir = base_dir / 'data/5-audio-chunks-espeak'
    output_dir = base_dir / 'data/6-audio-chapters-espeak'
    
    # Process files
    combine_audio_files(audio_dir, output_dir)
    print('Done!')

if __name__ == '__main__':
    main() 