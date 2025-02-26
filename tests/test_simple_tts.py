#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test script for simple_tts.py

This script demonstrates how to use the simple_tts.py module
to convert a single markdown file to audio.
"""

import os
import sys
from pathlib import Path
from simple_tts import process_markdown_file, VoiceSettings

def main():
    # Check if an API key is provided
    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        print("Error: ELEVENLABS_API_KEY environment variable is not set")
        print("Please set it before running this test, for example:")
        print("export ELEVENLABS_API_KEY='your_api_key_here'")
        sys.exit(1)
    
    # Set the file path for the test
    input_file = Path("data/4-markdown-chunks-optimized/chapter_30a-OPTIMIZED.md")
    if not input_file.exists():
        print(f"Error: Test file {input_file} does not exist")
        sys.exit(1)
    
    output_dir = Path("data/5-audio-chunks")
    
    # Create voice settings
    voice_settings = VoiceSettings(
        stability=0.5,
        similarity_boost=0.75,
        style=0.0,
        use_speaker_boost=True
    )
    
    # Process the file
    print(f"Processing file: {input_file}")
    success, result = process_markdown_file(
        input_file,
        output_dir,
        voice_id="OJtLHqR5g0hxcgc27j7C",  # Czech voice from elevenlabs_text_to_speech.sh
        model_id="eleven_multilingual_v2",
        voice_settings=voice_settings
    )
    
    if success:
        print(f"Success! Audio file generated: {result}")
        print("Now you can concatenate audio files into a chapter using audio_concat.py")
        print("Example: python audio_concat.py -c 30")
    else:
        print(f"Error: {result}")
        sys.exit(1)

if __name__ == "__main__":
    from elevenlabs import set_api_key
    
    # Set the API key
    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if api_key:
        set_api_key(api_key)
    
    main() 