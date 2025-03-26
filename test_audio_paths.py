#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test Audio Paths
---------------

This script verifies that audio files exist at the expected locations referenced
in the markdown files, and creates a test HTML page to check audio playback.
"""

import os
import re
import glob
from pathlib import Path
import shutil

# Base directories
TEXT_BASE_DIR = Path("./data/7-paragraphs/text")
AUDIO_BASE_DIR = Path("./data/7-paragraphs/audio")
OUTPUT_DIR = Path("./audio_test")

def create_test_html():
    """Create a test HTML file with direct audio links to verify playback."""
    # Create output directory
    OUTPUT_DIR.mkdir(exist_ok=True)
    
    # Sample chapters to test
    test_chapters = ["chapter_62", "chapter_145", "chapter_177"]
    
    html_content = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Audio Playback Test</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .audio-item { margin-bottom: 20px; border: 1px solid #ccc; padding: 10px; }
        h3 { margin-top: 5px; }
        .status { color: green; }
        .error { color: red; }
    </style>
</head>
<body>
    <h1>Audio Playback Test</h1>
    <p>This page tests direct audio playback from files. If you can't hear audio when clicking play, check the console for errors.</p>
    <div id="audio-container">
"""
    
    missing_files = []
    audio_entries = []
    
    for chapter in test_chapters:
        chapter_text_dir = TEXT_BASE_DIR / chapter
        chapter_audio_dir = AUDIO_BASE_DIR / chapter
        
        if not chapter_text_dir.exists() or not chapter_audio_dir.exists():
            print(f"Warning: Directory not found for {chapter}")
            continue
        
        # Get first 3 markdown files
        md_files = list(chapter_text_dir.glob("*.md"))[:3]
        
        for md_file in md_files:
            base_name = md_file.stem
            audio_file = chapter_audio_dir / f"{base_name}.mp3"
            
            # Check if audio file exists
            exists = audio_file.exists()
            
            # Read first 100 chars of text content
            with open(md_file, "r", encoding="utf-8") as f:
                text_preview = f.read(150) + "..."
            
            # Create relative path to audio file
            rel_audio_path = f"../data/7-paragraphs/audio/{chapter}/{base_name}.mp3"
            abs_audio_path = f"/data/7-paragraphs/audio/{chapter}/{base_name}.mp3"
            local_audio_path = f"audio/{base_name}.mp3"
            
            # Copy audio file to test directory if it exists
            test_audio_dir = OUTPUT_DIR / "audio"
            test_audio_dir.mkdir(exist_ok=True)
            
            if exists:
                try:
                    shutil.copy(audio_file, test_audio_dir / f"{base_name}.mp3")
                except Exception as e:
                    print(f"Error copying {audio_file}: {e}")
            else:
                missing_files.append(str(audio_file))
            
            # Add entry to HTML
            audio_entries.append(f"""
    <div class="audio-item">
        <h3>{chapter} - {base_name}</h3>
        <p>{text_preview}</p>
        <p class="{'status' if exists else 'error'}">Audio file: {'EXISTS' if exists else 'MISSING'}</p>
        
        <h4>Standard HTML5 Audio (using relative path)</h4>
        <audio controls>
            <source src="{rel_audio_path}" type="audio/mpeg">
            Your browser does not support the audio element.
        </audio>
        
        <h4>HTML5 Audio (using absolute path)</h4>
        <audio controls>
            <source src="{abs_audio_path}" type="audio/mpeg">
            Your browser does not support the audio element.
        </audio>
        
        <h4>HTML5 Audio (using local copy)</h4>
        <audio controls>
            <source src="{local_audio_path}" type="audio/mpeg">
            Your browser does not support the audio element.
        </audio>
    </div>
""")
    
    # Add audio entries to HTML
    html_content += "\n".join(audio_entries)
    
    # Close HTML
    html_content += """
    </div>
    <script>
        // Add event listeners to detect audio play errors
        document.querySelectorAll('audio').forEach(audio => {
            audio.addEventListener('error', function() {
                console.error('Error loading audio:', this.querySelector('source').src);
                this.insertAdjacentHTML('afterend', '<p class="error">Error loading audio file</p>');
            });
        });
    </script>
</body>
</html>
"""
    
    # Write HTML file
    with open(OUTPUT_DIR / "test.html", "w", encoding="utf-8") as f:
        f.write(html_content)
    
    print(f"Test HTML page created at {OUTPUT_DIR}/test.html")
    print(f"Missing audio files: {len(missing_files)}")
    for file in missing_files[:10]:  # Show first 10 missing files
        print(f" - {file}")
    if len(missing_files) > 10:
        print(f" ... and {len(missing_files) - 10} more")

def check_audio_references():
    """Check all markdown files for audio references and verify the files exist."""
    missing_count = 0
    total_count = 0
    
    for chapter_dir in TEXT_BASE_DIR.iterdir():
        if not chapter_dir.is_dir():
            continue
        
        chapter_name = chapter_dir.name
        chapter_audio_dir = AUDIO_BASE_DIR / chapter_name
        
        if not chapter_audio_dir.exists():
            print(f"Warning: Audio directory missing for {chapter_name}")
            continue
        
        for md_file in chapter_dir.glob("*.md"):
            total_count += 1
            base_name = md_file.stem
            audio_file = chapter_audio_dir / f"{base_name}.mp3"
            
            if not audio_file.exists():
                missing_count += 1
                print(f"Missing audio file: {audio_file}")
    
    print(f"Total markdown files: {total_count}")
    print(f"Missing audio files: {missing_count}")
    print(f"Audio files present: {total_count - missing_count} ({(total_count - missing_count) / total_count * 100:.1f}%)")

if __name__ == "__main__":
    print("Checking audio file references...")
    check_audio_references()
    print("\nCreating test HTML page...")
    create_test_html()
    print("\nDone! Open audio_test/test.html in your browser to test audio playback") 