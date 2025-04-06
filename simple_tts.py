#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Simple Text-to-Speech Wrapper
----------------------------

A simplified wrapper around the audio_chunk_generator.py module to provide
a consistent interface for testing.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

from audio_chunk_generator import process_markdown_file as process_file


@dataclass
class VoiceSettings:
    """Voice settings data class for ElevenLabs TTS"""

    stability: float = 0.5
    similarity_boost: float = 0.75
    style: float = 0.0
    use_speaker_boost: bool = True


def process_markdown_file(
    file_path: str,
    output_dir: str,
    voice_id: str = "OJtLHqR5g0hxcgc27j7C",
    model_id: str = "eleven_multilingual_v2",
    voice_settings: Optional[VoiceSettings] = None,
) -> Tuple[bool, str]:
    """
    Wrapper around audio_chunk_generator.process_markdown_file that accepts a VoiceSettings object

    Args:
        file_path: Path to the markdown file
        output_dir: Directory to save the audio file
        voice_id: ElevenLabs voice ID
        model_id: ElevenLabs model ID
        voice_settings: Voice settings object

    Returns:
        Tuple (success, output_file_path or error_message)
    """
    # Set default voice settings if not provided
    if voice_settings is None:
        voice_settings = VoiceSettings()

    # Pass the individual settings to the underlying function
    return process_file(
        file_path=file_path,
        output_dir=output_dir,
        voice_id=voice_id,
        model_id=model_id,
        stability=voice_settings.stability,
        similarity_boost=voice_settings.similarity_boost,
        style=voice_settings.style,
    )
