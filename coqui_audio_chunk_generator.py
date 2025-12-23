#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Coqui TTS Audio Chunk Generator
High-quality open-source alternative to ElevenLabs
"""

import logging
import os
import subprocess
from pathlib import Path
from typing import Dict, List, Any

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class CoquiAudioChunkGenerator:
    """
    Audio generator that uses Coqui TTS for high-quality open-source text-to-speech.
    This provides a free alternative to ElevenLabs with comparable quality.
    """

    def __init__(self, input_dir, output_dir, model_name="tts_models/multilingual/multi-dataset/xtts_v2", language="cs"):
        """
        Initialize the Coqui TTS audio generator.

        Args:
            input_dir: Directory containing markdown chunks to synthesize.
            output_dir: Directory to save generated audio files.
            model_name: Coqui TTS model to use (default: XTTS v2 multilingual)
            language: Language code for TTS (default: cs for Czech).
        """
        self.input_dir = Path(input_dir)
        # Organize output by engine: create coqui subdirectory
        base_output = Path(output_dir)
        self.output_dir = base_output / "coqui"
        self.language = language
        self.model_name = model_name

        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize Coqui TTS
        self._initialize_tts()

    def _initialize_tts(self):
        """Initialize Coqui TTS model."""
        try:
            from TTS.api import TTS
            
            logger.info(f"Loading Coqui TTS model: {self.model_name}")
            self.tts = TTS(model_name=self.model_name, progress_bar=True)
            logger.info("Coqui TTS model loaded successfully")
            
        except ImportError:
            logger.error("Coqui TTS not installed. Install with: pip install TTS")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize Coqui TTS: {e}")
            raise

    def _convert_to_mp3(self, wav_file: Path, mp3_file: Path):
        """Convert WAV file to MP3 using ffmpeg."""
        try:
            cmd = [
                "ffmpeg", "-i", str(wav_file), 
                "-codec:a", "libmp3lame", 
                "-qscale:a", "2", 
                str(mp3_file), 
                "-y"  # Overwrite output file
            ]
            subprocess.run(cmd, check=True, capture_output=True)
            logger.debug(f"Converted {wav_file.name} to {mp3_file.name}")
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg conversion failed: {e}")
            raise
        except FileNotFoundError:
            logger.error("FFmpeg not found. Please install ffmpeg.")
            raise

    def synthesize_chunk(self, input_file: Path, speaker_wav: str = None):
        """
        Synthesize a single chunk using Coqui TTS.

        Args:
            input_file: Path to markdown file to synthesize.
            speaker_wav: Optional path to reference audio for voice cloning.

        Returns:
            Path to the generated audio file.
        """
        # Get the stem name from the input file (without extension)
        base_name = input_file.stem.replace("-OPTIMIZED", "")
        wav_output = self.output_dir / f"{base_name}.wav"
        mp3_output = self.output_dir / f"{base_name}.mp3"

        logger.info(f"Synthesizing {input_file.name} with Coqui TTS")

        # Read the markdown content
        with open(input_file, "r", encoding="utf-8") as f:
            text = f.read()

        if not text.strip():
            logger.warning(f"File {input_file.name} is empty or contains only whitespace")
            return None

        try:
            # Generate audio with Coqui TTS
            self.tts.tts_to_file(
                text=text,
                file_path=str(wav_output),
                speaker_wav=speaker_wav,
                language=self.language
            )

            # Convert WAV to MP3 for consistency with other generators
            self._convert_to_mp3(wav_output, mp3_output)
            
            # Remove WAV file to save space
            wav_output.unlink()

            logger.info(f"Successfully generated: {mp3_output.name}")
            return mp3_output

        except Exception as e:
            logger.error(f"Error synthesizing {input_file.name}: {e}")
            # Clean up partial files
            if wav_output.exists():
                wav_output.unlink()
            if mp3_output.exists():
                mp3_output.unlink()
            return None

    def process(self, directory=None, speaker_wav=None) -> Dict[str, Any]:
        """
        Process all markdown files in the input directory.

        Args:
            directory: Optional override for input directory.
            speaker_wav: Optional path to reference audio for voice cloning.

        Returns:
            Dictionary with processing results.
        """
        directory = directory or self.input_dir
        input_files = sorted(list(Path(directory).glob("*.md")))

        if not input_files:
            logger.warning(f"No markdown files found in {directory}")
            return {
                "success": True,
                "processed_files": [],
                "stats": {"input_count": 0, "output_count": 0, "failed_count": 0}
            }

        logger.info(f"Processing {len(input_files)} files with Coqui TTS")

        output_files = []
        failed_files = []
        
        for input_file in input_files:
            try:
                output_file = self.synthesize_chunk(input_file, speaker_wav)
                if output_file:
                    output_files.append(output_file)
                else:
                    failed_files.append(input_file.name)
            except Exception as e:
                logger.error(f"Failed to process {input_file.name}: {e}")
                failed_files.append(input_file.name)

        # Mark processed files (similar to ElevenLabs generator)
        for input_file in input_files:
            if input_file.name not in failed_files:
                try:
                    new_name = input_file.parent / f"AUDIO_GENERATED-{input_file.name}"
                    input_file.rename(new_name)
                    logger.info(f"Marked as processed: {new_name.name}")
                except OSError as e:
                    logger.warning(f"Could not rename processed file {input_file.name}: {e}")

        result = {
            "success": len(failed_files) == 0,
            "processed_files": [str(f) for f in output_files],
            "failed_files": failed_files,
            "stats": {
                "input_count": len(input_files),
                "output_count": len(output_files),
                "failed_count": len(failed_files)
            }
        }

        logger.info(f"Coqui TTS processing completed: {len(output_files)} successful, {len(failed_files)} failed")
        return result


def main():
    """Main entry point for command-line use."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Coqui TTS Audio Chunk Generator",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument("input_dir", type=str, help="Input directory containing markdown files")
    parser.add_argument("output_dir", type=str, help="Output directory for audio files")
    parser.add_argument(
        "--model", 
        type=str, 
        default="tts_models/multilingual/multi-dataset/xtts_v2",
        help="Coqui TTS model to use"
    )
    parser.add_argument(
        "--language", 
        type=str, 
        default="cs",
        help="Language code for TTS"
    )
    parser.add_argument(
        "--speaker-wav",
        type=str,
        help="Optional path to reference audio for voice cloning"
    )

    args = parser.parse_args()

    try:
        generator = CoquiAudioChunkGenerator(
            input_dir=args.input_dir,
            output_dir=args.output_dir,
            model_name=args.model,
            language=args.language
        )

        result = generator.process(speaker_wav=args.speaker_wav)

        if result["success"]:
            logger.info("Processing completed successfully.")
        else:
            logger.error(f"Processing completed with {result['stats']['failed_count']} failures.")
            return 1

        return 0

    except Exception as e:
        logger.error(f"Error: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
