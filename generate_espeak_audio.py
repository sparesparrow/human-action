#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Espeak-NG Audio Generation Script
---------------------------------

This script processes all remaining markdown files that haven't been converted to audio yet,
using espeak-ng for text-to-speech. It keeps track of progress in a separate file and
outputs to a different directory than the original ElevenLabs audio files.
"""

import argparse
import glob
import json
import logging
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

# Try to import optional modules with fallbacks
try:
    from tqdm import tqdm
except ImportError:
    # Define a simple tqdm replacement if the module is not available
    class tqdm:
        @staticmethod
        def tqdm(iterable, **kwargs):
            print(f"Processing {len(iterable)} files...")
            return iterable

    tqdm = tqdm.tqdm

try:
    import espeakng

    ESPEAK_AVAILABLE = True
except ImportError:
    ESPEAK_AVAILABLE = False
    print(
        "Warning: espeakng module not found. Will use command-line espeak-ng instead."
    )

try:
    import yaml
except ImportError:
    yaml = None
    print("Warning: yaml module not found. Config file loading will be disabled.")

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("espeak_generation.log"),
    ],
)
logger = logging.getLogger(__name__)

# Constants
PROGRESS_FILE = "espeak_progress.json"
DEFAULT_INPUT_DIR = "./data/4-markdown-chunks-optimized"
DEFAULT_OUTPUT_DIR = "./data/5-audio-chunks-espeak"
FFMPEG_QUALITY = "2"  # Add this constant for the ffmpeg quality setting
TEMP_FILE_PREFIX = "temp_"  # Add this for temp file naming


def process_markdown_file(
    file_path: Path,
    output_dir: Path,
    voice: str,
    rate: int = 175,
    pitch: int = 50,
    volume: int = 100,
) -> tuple[bool, str]:
    """
    Process a single markdown file to generate audio using espeak-ng.

    Args:
        file_path: Path to the markdown file
        output_dir: Directory to save the audio file
        voice: Espeak voice to use (e.g., 'cs', 'en', 'es')
        rate: Speech rate (words per minute)
        pitch: Voice pitch (0-100)
        volume: Audio volume (0-100)

    Returns:
        Tuple (success, output_file_path)
    """
    try:
        # Create Path objects
        file_path = Path(
            file_path
        )  # i.e. data/4-markdown-chunks-optimized/chapter_30a-OPTIMIZED.md
        output_dir = Path(output_dir)  # data/5-audio-chunks

        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)

        # Get base name without -OPTIMIZED suffix
        base_name = file_path.stem.replace("-OPTIMIZED", "")  # i.e. chapter_30a.md
        wav_output_file = output_dir / f"{base_name}.wav"  # For initial WAV output
        mp3_output_file = output_dir / f"{base_name}.mp3"  # Final MP3 output

        logger.info(f"Processing file: {file_path.name} -> {mp3_output_file.name}")

        # Read content from the markdown file
        with open(file_path, "r", encoding="utf-8") as f:
            text_content = f.read()

        if not text_content.strip():
            logger.warning(
                f"File {file_path.name} is empty or contains only whitespace"
            )
            return False, f"File {file_path.name} is empty"

        # Initialize espeak-ng
        logger.info(f"Generating audio for {file_path.name} using espeak-ng...")

        if ESPEAK_AVAILABLE:
            try:
                # Initialize the ESpeakNG instance
                esng = espeakng.Speaker()
                esng.voice = voice
                esng.speed = rate
                esng.pitch = pitch
                esng.volume = volume

                # Save to WAV file
                esng.save_to_file(text_content, str(wav_output_file))

                # Convert WAV to MP3 using ffmpeg (better quality and smaller file)
                logger.info(f"Converting WAV to MP3...")
                ffmpeg_cmd = [
                    "ffmpeg",
                    "-y",
                    "-i",
                    str(wav_output_file),
                    "-codec:a",
                    "libmp3lame",
                    "-qscale:a",
                    FFMPEG_QUALITY,
                    str(mp3_output_file),
                ]
                with subprocess.Popen(
                    ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
                ) as proc:
                    stdout, stderr = proc.communicate()
                    if proc.returncode != 0:
                        raise subprocess.CalledProcessError(
                            proc.returncode, ffmpeg_cmd, stderr
                        )

                # Remove the intermediate WAV file
                if wav_output_file.exists():
                    wav_output_file.unlink()

            except Exception as e:
                logger.error(f"Error with espeakng: {str(e)}")
                # Fall back to command-line approach
                logger.info("Falling back to espeak-ng command line...")
                raise RuntimeError("Falling back to command-line approach")
        else:
            # Always use command-line approach if espeakng not available
            logger.info("Using espeak-ng command line (Python module not available)...")
            raise RuntimeError("Using command-line approach")

        # If we reach here with ESPEAK_AVAILABLE, we succeeded with the Python module

        # Rename the processed markdown file by adding prefix
        new_name = file_path.parent / f"ESPEAK_AUDIO-{file_path.name}"
        file_path.rename(new_name)

        logger.info(f"Successfully generated: {mp3_output_file}")
        logger.info(f"Renamed processed file to: {new_name.name}")

        return True, str(mp3_output_file)

    except RuntimeError as re:
        # This is our signal to use the command-line approach
        try:
            # Save text to a temporary file (to handle potential command line length issues)
            temp_text_file = output_dir / f"{TEMP_FILE_PREFIX}{base_name}.txt"
            with open(temp_text_file, "w", encoding="utf-8") as f:
                f.write(text_content)

            # Use espeak-ng command line
            espeak_cmd = [
                "espeak-ng",
                "-v",
                voice,
                "-s",
                str(rate),
                "-p",
                str(pitch),
                "-a",
                str(volume),
                "-f",
                str(temp_text_file),
                "-w",
                str(wav_output_file),
            ]
            subprocess.run(
                espeak_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )

            # Convert WAV to MP3 using ffmpeg
            ffmpeg_cmd = [
                "ffmpeg",
                "-y",
                "-i",
                str(wav_output_file),
                "-codec:a",
                "libmp3lame",
                "-qscale:a",
                FFMPEG_QUALITY,
                str(mp3_output_file),
            ]
            subprocess.run(
                ffmpeg_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )

            # Remove temporary files
            cleanup_temp_files(wav_output_file, temp_text_file)

            # Rename the processed markdown file by adding prefix
            new_name = file_path.parent / f"ESPEAK_AUDIO-{file_path.name}"
            file_path.rename(new_name)

            logger.info(f"Successfully generated using command line: {mp3_output_file}")
            return True, str(mp3_output_file)

        except Exception as cmd_e:
            error_msg = f"Command-line fallback failed: {str(cmd_e)}"
            logger.error(error_msg)
            return False, error_msg

    except Exception as e:
        error_msg = f"Error processing {file_path.name}: {str(e)}"
        logger.error(error_msg)
        return False, error_msg


def load_progress(progress_file: Path) -> Dict[str, Any]:
    """Load progress from JSON file."""
    if progress_file.exists():
        try:
            with open(progress_file, "r", encoding="utf-8") as f:
                content = f.read()
                if not content:
                    logger.warning(f"Progress file {progress_file} is empty.")
                    return {}
                progress_data: Dict[str, Any] = json.loads(content)
                return progress_data
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON from {progress_file}: {e}")
            # Handle error: return empty dict or raise exception
            return {}
        except Exception as e:
            logger.error(f"Error reading progress file {progress_file}: {e}")
            return {}
    return {}


def save_progress(progress):
    """Save processing progress to JSON file."""
    progress["last_run"] = datetime.now().isoformat()
    with open(PROGRESS_FILE, "w") as f:
        json.dump(progress, f, indent=2)


def find_remaining_files(input_dir, progress):
    """Find markdown files that haven't been processed yet."""
    all_files = glob.glob(f"{input_dir}/*-OPTIMIZED.md")
    processed_files = set(progress["processed_files"] + progress["failed_files"])

    # Filter out files that have already been processed or have AUDIO_GENERATED prefix
    remaining_files = []
    for file in all_files:
        file_path = Path(file)
        if (
            file not in processed_files
            and not file_path.name.startswith("AUDIO_GENERATED-")
            and not file_path.name.startswith("ESPEAK_AUDIO-")
        ):
            remaining_files.append(file)

    return remaining_files


def load_config(config_file: str = "config.yaml") -> dict:
    """Load configuration from YAML file."""
    if yaml is None:
        logger.warning("YAML module not available, cannot load config file")
        return {}

    if os.path.exists(config_file):
        with open(config_file, "r") as f:
            return yaml.safe_load(f)
    return {}


def cleanup_temp_files(*files: Path) -> None:
    """Clean up temporary files safely."""
    for file in files:
        try:
            if file.exists():
                file.unlink()
        except Exception as e:
            logger.warning(f"Failed to remove temporary file {file}: {e}")


def validate_args(args: argparse.Namespace) -> None:
    """Validate command line arguments."""
    if not (80 <= args.rate <= 500):
        raise ValueError("Speech rate must be between 80 and 500")
    if not (0 <= args.pitch <= 100):
        raise ValueError("Pitch must be between 0 and 100")
    if not (0 <= args.volume <= 100):
        raise ValueError("Volume must be between 0 and 100")


def print_summary(progress: dict) -> None:
    """Print detailed progress summary."""
    print("\nProgress Summary:")
    print(f"Total files processed: {progress['total_processed']}")
    print(f"Successfully processed: {len(progress['processed_files'])}")
    print(f"Failed files: {len(progress['failed_files'])}")
    print(f"Last run: {progress['last_run']}")


def main():
    parser = argparse.ArgumentParser(
        description="Espeak-NG Audio Generation for Remaining Files",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "-i",
        "--input-dir",
        type=str,
        default=DEFAULT_INPUT_DIR,
        help="Directory containing optimized markdown files",
    )

    parser.add_argument(
        "-o",
        "--output-dir",
        type=str,
        default=DEFAULT_OUTPUT_DIR,
        help="Output directory for espeak audio files",
    )

    parser.add_argument(
        "-v",
        "--voice",
        type=str,
        default="cs",
        help="Espeak-NG voice to use (e.g., cs, en, en-gb)",
    )

    parser.add_argument(
        "-r",
        "--rate",
        type=int,
        default=175,
        help="Speech rate (words per minute, 80-500)",
    )

    parser.add_argument(
        "-p", "--pitch", type=int, default=50, help="Voice pitch (0-100)"
    )

    parser.add_argument("--volume", type=int, default=100, help="Audio volume (0-100)")

    parser.add_argument(
        "--max-files",
        type=int,
        default=0,
        help="Maximum number of files to process (0 for all remaining)",
    )

    parser.add_argument(
        "--ignore-progress",
        action="store_true",
        help="Ignore the saved progress and process all files from scratch",
    )

    args = parser.parse_args()

    # Validate arguments
    validate_args(args)

    # Load or reset progress based on the ignore-progress flag
    if args.ignore_progress:
        logger.info("Ignoring saved progress. Resetting progress data.")
        progress = {
            "processed_files": [],
            "failed_files": [],
            "total_processed": 0,
            "total_failed": 0,
            "last_run": None,
        }
    else:
        progress = load_progress()

    logger.info(
        f"Loaded progress: {progress['total_processed']} processed, {progress['total_failed']} failed"
    )

    # Find remaining files
    remaining_files = find_remaining_files(args.input_dir, progress)
    logger.info(f"Found {len(remaining_files)} files to process")

    if not remaining_files:
        logger.info("No files to process. All done!")
        return

    # Limit the number of files if specified
    if args.max_files > 0 and len(remaining_files) > args.max_files:
        remaining_files = remaining_files[: args.max_files]
        logger.info(f"Limited to {args.max_files} files")

    # Process each file
    success_count = 0
    fail_count = 0

    for file in tqdm(remaining_files, desc="Processing files"):
        logger.info(f"Processing file: {file}")

        success, result = process_markdown_file(
            file, args.output_dir, args.voice, args.rate, args.pitch, args.volume
        )

        # Update progress
        if success:
            success_count += 1
            progress["processed_files"].append(file)
            progress["total_processed"] += 1
            logger.info(f"Successfully processed: {file}")
        else:
            fail_count += 1
            progress["failed_files"].append(file)
            progress["total_failed"] += 1
            logger.error(f"Failed to process: {file} - {result}")

        # Save progress after each file
        save_progress(progress)

    # Final report
    logger.info(f"Processing complete: {success_count} succeeded, {fail_count} failed")
    logger.info(
        f"Total processed: {progress['total_processed']}, Total failed: {progress['total_failed']}"
    )
    logger.info(f"Progress saved to {PROGRESS_FILE}")

    # Print summary
    print_summary(progress)


if __name__ == "__main__":
    main()
