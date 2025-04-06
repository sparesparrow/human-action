# -*- coding: utf-8 -*-

"""
Unified configuration for the audio book generation pipeline
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional

import yaml


class Config:
    def __init__(self, config_file="config.yaml"):
        self.config_path = Path(config_file)
        self.config: Dict[str, Any] = self._load_config()

        # Set up base directories
        self.base_dir: Path = Path(self.config.get("base_dir", "."))

        # Declare directory path attributes for static analysis
        self.pdf_dir: Optional[Path] = None
        self.markdown_chapters_dir: Optional[Path] = None
        self.markdown_chunks_dir: Optional[Path] = None
        self.optimized_chunks_dir: Optional[Path] = None
        self.audio_chunks_dir: Optional[Path] = None
        self.audio_chapters_dir: Optional[Path] = None
        self.paragraphs_dir: Optional[Path] = None
        self.audio_book_dir: Optional[Path] = None

        self.initialize_directories()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        if not self.config_path.exists():
            return self._create_default_config()

        with open(self.config_path, "r") as f:
            return yaml.safe_load(f)

    def _create_default_config(self):
        """Create a default configuration"""
        default_config = {
            "base_dir": ".",
            "directories": {
                "pdf": "data/1-pdf",
                "markdown_chapters": "data/2-markdown-chapters",
                "markdown_chunks": "data/3-markdown-chunks",
                "optimized_chunks": "data/4-markdown-chunks-optimized",
                "audio_chunks": "data/5-audio-chunks-espeak",
                "audio_chapters": "data/6-audio-chapters-espeak",
                "paragraphs": "data/7-paragraphs",
            },
            "tts": {
                "engine": "espeak-ng",
                "voice": "cs",
                "rate": 175,
                "pitch": 50,
                "volume": 100,
            },
            "chunking": {"max_chunk_size": 5000},
            "processing": {"parallel_jobs": 4},
        }

        # Save default config
        with open(self.config_path, "w") as f:
            yaml.dump(default_config, f, default_flow_style=False)

        return default_config

    def initialize_directories(self):
        """Create all required directories"""
        for dir_name, dir_path in self.config["directories"].items():
            full_path = self.base_dir / dir_path
            full_path.mkdir(parents=True, exist_ok=True)

            # Store the full path in the config
            setattr(self, f"{dir_name}_dir", full_path)

    def get_path(self, key: str) -> Optional[Path]:
        """Get a directory path by key"""
        dir_path = self.config["directories"].get(key)
        if dir_path:
            return self.base_dir / dir_path
        return None
