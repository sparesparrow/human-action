#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Piper TTS Audio Chunk Generator
Fast, local neural text-to-speech system optimized for devices
"""

import json
import logging
import os
import subprocess
import shutil
from pathlib import Path
from typing import Dict, List, Any, Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class PiperAudioChunkGenerator:
    """
    Audio generator that uses Piper TTS for fast, local text-to-speech.
    Piper is optimized for devices like Raspberry Pi with excellent Czech support.
    """

    def __init__(self, input_dir, output_dir, model_name="cs_CZ-jirka-medium", language="cs", keep_wav=True, upsample=True,
                 length_scale=1.0, noise_scale=0.667, noise_w=0.8):
        """
        Initialize the Piper TTS audio generator.

        Args:
            input_dir: Directory containing markdown chunks to synthesize.
            output_dir: Directory to save generated audio files.
            model_name: Piper voice model to use (default: Czech voice)
            language: Language code for TTS (default: cs for Czech).
            keep_wav: If True, keep WAV files instead of converting (lossless quality, recommended)
            upsample: If True, upsample 22050 Hz to 44100 Hz when converting (improves quality)
            length_scale: Speech speed multiplier (0.8-1.2, default 1.0)
            noise_scale: Stability/variation level (0.3-0.8, default 0.667)
            noise_w: Phoneme width variation (0.5-1.0, default 0.8)
        """
        self.input_dir = Path(input_dir)
        # Organize output by engine: create piper subdirectory
        base_output = Path(output_dir)
        self.output_dir = base_output / "piper"
        self.language = language
        self.model_name = model_name
        self.keep_wav = keep_wav  # Option to keep WAV for maximum quality
        self.upsample = upsample  # Option to upsample for better quality

        # Voice synthesis parameters for quality control
        self.length_scale = length_scale  # Speech speed
        self.noise_scale = noise_scale    # Stability/variation
        self.noise_w = noise_w           # Phoneme width

        # Define parameter presets for different voice styles
        self.presets = {
            'natural': {
                'length_scale': 1.0,
                'noise_scale': 0.667,
                'noise_w': 0.8
            },
            'clear': {
                'length_scale': 1.0,
                'noise_scale': 0.5,
                'noise_w': 0.7
            },
            'expressive': {
                'length_scale': 1.0,
                'noise_scale': 0.8,
                'noise_w': 0.9
            },
            'fast': {
                'length_scale': 1.2,
                'noise_scale': 0.6,
                'noise_w': 0.8
            },
            'slow': {
                'length_scale': 0.8,
                'noise_scale': 0.5,
                'noise_w': 0.7
            }
        }

        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Piper paths
        self.piper_binary = self._find_piper_binary()
        self.models_dir = Path.home() / ".piper" / "models"

        # Check if requests library is available for downloads
        try:
            import requests
            self._use_requests = True
        except ImportError:
            self._use_requests = False

        # Initialize Piper TTS
        self._initialize_piper()

    @staticmethod
    def _find_piper_binary() -> Optional[Path]:
        """Find Piper binary in system PATH."""
        piper_paths = [
            shutil.which("piper"),
            shutil.which("piper-tts"),
            "/usr/local/bin/piper",
            "/usr/bin/piper",
            "./piper",  # Local binary
        ]

        for path in piper_paths:
            if path and Path(path).exists():
                return Path(path)

        return None

    def _initialize_piper(self):
        """Initialize Piper TTS and download models if needed."""
        if not self.piper_binary:
            logger.warning("Piper binary not found. Install Piper TTS from https://github.com/rhasspy/piper")
            logger.info("On Ubuntu/Debian: download piper_amd64.tar.gz and extract to /usr/local/bin/")
            raise ImportError("Piper binary not found")

        # Ensure models directory exists
        self.models_dir.mkdir(parents=True, exist_ok=True)

        # Check if model exists, download if needed
        model_file = self.models_dir / f"{self.model_name}.onnx"
        config_file = self.models_dir / f"{self.model_name}.onnx.json"

        if not model_file.exists() or not config_file.exists():
            logger.info(f"Downloading Piper model: {self.model_name}")
            self._download_piper_model()

        logger.info("Piper TTS initialized successfully")

    def apply_preset(self, preset_name: str):
        """
        Apply a parameter preset for different voice styles.

        Args:
            preset_name: Name of the preset ('natural', 'clear', 'expressive', 'fast', 'slow')
        """
        if preset_name not in self.presets:
            logger.warning(f"Unknown preset '{preset_name}', available: {list(self.presets.keys())}")
            return

        preset = self.presets[preset_name]
        self.length_scale = preset['length_scale']
        self.noise_scale = preset['noise_scale']
        self.noise_w = preset['noise_w']

        logger.info(f"Applied preset '{preset_name}': length_scale={self.length_scale}, "
                   f"noise_scale={self.noise_scale}, noise_w={self.noise_w}")

    def set_parameters(self, length_scale=None, noise_scale=None, noise_w=None):
        """
        Manually set synthesis parameters.

        Args:
            length_scale: Speech speed multiplier (0.8-1.2)
            noise_scale: Stability/variation level (0.3-0.8)
            noise_w: Phoneme width variation (0.5-1.0)
        """
        if length_scale is not None:
            self.length_scale = max(0.5, min(2.0, length_scale))  # Clamp to reasonable range
        if noise_scale is not None:
            self.noise_scale = max(0.1, min(1.0, noise_scale))
        if noise_w is not None:
            self.noise_w = max(0.1, min(1.5, noise_w))

    def get_current_parameters(self) -> Dict[str, float]:
        """
        Get current synthesis parameter values.

        Returns:
            Dictionary with current parameter values
        """
        return {
            'length_scale': self.length_scale,
            'noise_scale': self.noise_scale,
            'noise_w': self.noise_w
        }

    def _download_piper_model(self):
        """Download Piper voice model from HuggingFace."""
        try:
            # Try to import requests for downloading
            try:
                import requests
                use_requests = True
            except ImportError:
                import urllib.request
                import urllib.error
                use_requests = False

            # Create models directory
            self.models_dir.mkdir(parents=True, exist_ok=True)

            # Model URLs - Piper models follow the pattern: cs/cs_CZ/jirka/medium/cs_CZ-jirka-medium.onnx
            base_url = "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0"
            # For Czech jirka medium, the path is: cs/cs_CZ/jirka/medium/cs_CZ-jirka-medium
            if self.model_name == "cs_CZ-jirka-medium":
                model_path = "cs/cs_CZ/jirka/medium/cs_CZ-jirka-medium"
            else:
                # For other models, try the general pattern
                model_path = f"{self.model_name.replace('-', '/')}/{self.model_name}"

            model_url = f"{base_url}/{model_path}.onnx"
            config_url = f"{base_url}/{model_path}.onnx.json"

            model_file = self.models_dir / f"{self.model_name}.onnx"
            config_file = self.models_dir / f"{self.model_name}.onnx.json"

            # Download model file (~50MB)
            logger.info(f"Downloading Piper model: {self.model_name}")
            logger.info(f"Model URL: {model_url}")
            self._download_file(model_url, model_file, "model")

            # Download config file
            logger.info(f"Downloading Piper config: {self.model_name}")
            logger.info(f"Config URL: {config_url}")
            self._download_file(config_url, config_file, "config")

            # Verify files exist and have content
            if not model_file.exists() or model_file.stat().st_size == 0:
                raise FileNotFoundError(f"Model file download failed: {model_file}")
            if not config_file.exists() or config_file.stat().st_size == 0:
                raise FileNotFoundError(f"Config file download failed: {config_file}")

            logger.info(f"Successfully downloaded Piper model: {self.model_name}")

        except Exception as e:
            logger.error(f"Failed to download Piper model: {e}")
            logger.info("You can download models manually from: https://huggingface.co/rhasspy/piper-voices/tree/v1.0.0")
            raise

    def _download_file(self, url: str, dest_path: Path, file_type: str):
        """Download a file with progress indication."""
        try:
            if self._use_requests:
                # Use requests library
                import requests
                response = requests.get(url, stream=True)
                response.raise_for_status()

                total_size = int(response.headers.get('content-length', 0))
                downloaded = 0

                with open(dest_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total_size > 0:
                                progress = (downloaded / total_size) * 100
                                print(f"\rDownloading {file_type}: {progress:.1f}%", end='', flush=True)

                print()  # New line after progress

            else:
                # Use urllib as fallback
                import urllib.request
                import urllib.error

                # Get file size for progress (approximate)
                try:
                    with urllib.request.urlopen(url) as response:
                        total_size = int(response.headers.get('Content-Length', 0))
                except:
                    total_size = 0

                def progress_hook(blocks, block_size, total_size):
                    if total_size > 0:
                        downloaded = blocks * block_size
                        progress = (downloaded / total_size) * 100
                        print(f"\rDownloading {file_type}: {progress:.1f}%", end='', flush=True)

                urllib.request.urlretrieve(url, dest_path, progress_hook)
                print()  # New line after progress

        except Exception as e:
            logger.error(f"Failed to download {file_type} from {url}: {e}")
            raise

    def synthesize_chunk(self, input_file: Path, speaker_wav: Optional[str] = None,
                        length_scale: Optional[float] = None, noise_scale: Optional[float] = None,
                        noise_w: Optional[float] = None) -> Optional[Path]:
        """
        Synthesize a single chunk using Piper TTS.

        Args:
            input_file: Path to markdown file to synthesize.
            speaker_wav: Optional speaker WAV file for voice cloning (Piper doesn't support this).
            length_scale: Optional speech speed override (0.8-1.2)
            noise_scale: Optional stability override (0.3-0.8)
            noise_w: Optional phoneme width override (0.5-1.0)

        Returns:
            Path to the generated audio file.
        """
        # Get the stem name from the input file (without extension)
        base_name = input_file.stem.replace("-OPTIMIZED", "")
        # Use WAV if keep_wav is True, otherwise OGG (better quality than MP3)
        output_file = self.output_dir / f"{base_name}.{'wav' if self.keep_wav else 'ogg'}"

        # Read the markdown content
        with open(input_file, "r", encoding="utf-8") as f:
            text = f.read()

        if not text.strip():
            logger.warning(f"File {input_file.name} is empty or contains only whitespace")
            return None

        try:
            # Use Piper command-line interface with parameter overrides
            self._synthesize_with_piper_cli(text, output_file, length_scale, noise_scale, noise_w)
            logger.info(f"Successfully generated: {output_file.name}")
            return output_file

        except Exception as e:
            logger.error(f"Error synthesizing {input_file.name}: {e}")
            # Clean up partial files
            if output_file.exists():
                output_file.unlink()
            return None

    def _synthesize_with_piper_cli(self, text: str, output_file: Path,
                                  length_scale: Optional[float] = None, noise_scale: Optional[float] = None,
                                  noise_w: Optional[float] = None):
        """Synthesize text using Piper command-line interface."""
        model_file = self.models_dir / f"{self.model_name}.onnx"


        # Piper always outputs WAV format
        # If we want OGG/MP3, we need to output to a temp WAV file first, then convert
        # If keep_wav is True, output directly as WAV (no conversion, lossless quality)
        if output_file.suffix.lower() in [".mp3", ".ogg"] and not self.keep_wav:
            temp_wav_file = output_file.with_suffix(".wav")
            piper_output_file = temp_wav_file
            needs_conversion = True
        else:
            piper_output_file = output_file
            needs_conversion = False

        # Use parameter overrides or instance defaults
        final_length_scale = length_scale if length_scale is not None else self.length_scale
        final_noise_scale = noise_scale if noise_scale is not None else self.noise_scale
        final_noise_w = noise_w if noise_w is not None else self.noise_w

        # Piper command with configurable parameters
        # Note: Piper outputs 22050 Hz mono by default (model limitation)
        # We optimize quality parameters for best output
        cmd = [
            str(self.piper_binary),
            "--model", str(model_file),
            "--output_file", str(piper_output_file),
            "--espeak_data", "/usr/lib/x86_64-linux-gnu/espeak-ng-data",
            "--length_scale", str(final_length_scale),  # Speech speed
            "--noise_scale", str(final_noise_scale),    # Stability/variation
            "--noise_w", str(final_noise_w)             # Phoneme width
        ]

        try:
            # Run Piper with text input via stdin
            process = subprocess.run(
                cmd,
                input=text,
                text=True,
                capture_output=True,
                check=True
            )
            

            # If keeping WAV and upsampling is enabled, upsample the WAV file
            if not needs_conversion and self.keep_wav and self.upsample:
                # Upsample WAV to 44100 Hz for better quality
                # Use temp file with .wav extension for FFmpeg compatibility
                upsampled_wav = output_file.parent / f"{output_file.stem}.upsampled.wav"
                self._upsample_wav(piper_output_file, upsampled_wav)
                # Replace original with upsampled version
                piper_output_file.unlink()
                upsampled_wav.rename(output_file)
                return output_file

            # Convert WAV to OGG/MP3 if needed
            if needs_conversion:
                self._convert_wav_to_mp3(temp_wav_file, output_file)
                return output_file
            
            # Return WAV file as-is if no conversion needed
            return output_file

        except subprocess.CalledProcessError as e:
            logger.error(f"Piper command failed: {e}")
            logger.error(f"stdout: {e.stdout}")
            logger.error(f"stderr: {e.stderr}")
            raise

    def _convert_wav_to_mp3(self, wav_file: Path, mp3_file: Path):
        """Convert WAV file to MP3 using ffmpeg."""
        try:
            # Get WAV file info before conversion
            import subprocess as sp
            probe_cmd = ["ffprobe", "-v", "error", "-show_entries", "stream=sample_rate,channels,bit_rate", "-of", "json", str(wav_file)]
            try:
                probe_result = sp.run(probe_cmd, capture_output=True, text=True, check=True)
                wav_info = json.loads(probe_result.stdout)
            except Exception as e:
                wav_info = {"error": str(e)}
            
            # Upsample to 44100 Hz for better quality (Piper outputs 22050 Hz)
            # Use high-quality resampling algorithm (soxr) for best results
            # Then encode with maximum quality settings
            resample_filter = "-af" if self.upsample else ""
            resample_value = "aresample=resampler=soxr:osr=44100" if self.upsample else ""
            target_sample_rate = "44100" if self.upsample else "22050"
            
            if mp3_file.suffix.lower() == '.ogg':
                # Use OGG Vorbis quality 10 with optional upsampling
                cmd = [
                    "ffmpeg", "-i", str(wav_file),
                ]
                if self.upsample:
                    cmd.extend(["-af", "aresample=resampler=soxr:osr=44100"])
                cmd.extend([
                    "-codec:a", "libvorbis",
                    "-q:a", "10",  # Vorbis quality 10 = maximum (0-10 scale, 10 is best)
                    "-ar", target_sample_rate,  # Target sample rate
                    "-ac", "1",  # Preserve mono
                    str(mp3_file), "-y"
                ])
            else:
                # MP3 encoding with optional upsampling
                cmd = [
                    "ffmpeg", "-i", str(wav_file),
                ]
                if self.upsample:
                    cmd.extend(["-af", "aresample=resampler=soxr:osr=44100"])
                cmd.extend([
                    "-codec:a", "libmp3lame",
                    "-b:a", "320k",  # Target 320kbps
                    "-q:a", "2",  # VBR quality 2 (high quality, 0-9 scale)
                    "-ar", target_sample_rate,  # Target sample rate
                    "-ac", "1",  # Preserve mono
                    str(mp3_file), "-y"
                ])
            
            
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            
            
            logger.debug(f"Converted {wav_file.name} to {mp3_file.name}")

            # Remove original WAV file
            wav_file.unlink()

        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg conversion failed: {e}")
            raise
        except FileNotFoundError:
            logger.warning("FFmpeg not found, keeping WAV file")
            # Rename WAV to MP3 extension (not ideal but better than failing)
            if wav_file != mp3_file:
                wav_file.rename(mp3_file)

    def _upsample_wav(self, wav_file: Path, output_file: Path):
        """Upsample and enhance WAV file from 22050 Hz to 44100 Hz with audio enhancement."""
        try:
            
            # Apply audio enhancement: upsampling + fast normalization + EQ for voice clarity
            # Using dynaudnorm for faster normalization (single-pass) instead of loudnorm (two-pass)
            # Chain: upsample -> dynamic normalize -> EQ -> pad
            cmd = [
                "ffmpeg", "-i", str(wav_file),
                "-filter_complex",
                "[0:a]aresample=resampler=soxr:osr=44100[resampled];"
                "[resampled]dynaudnorm=f=150:g=15:p=0.95:m=5.0[normalized];"
                "[normalized]equalizer=f=100:width_type=h:width=200:g=-2,equalizer=f=2500:width_type=h:width=1000:g=3[eq];"
                "[eq]apad=pad_dur=0.3[out]",
                "-map", "[out]",
                "-ar", "44100",  # Target sample rate
                "-ac", "1",  # Preserve mono
                "-codec:a", "pcm_s16le",  # Keep PCM 16-bit
                "-f", "wav",  # Explicitly specify WAV format
                str(output_file), "-y"
            ]
            
            
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            
            
            logger.debug(f"Upsampled and enhanced {wav_file.name} to 44100 Hz")
            
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg audio enhancement failed: {e}")
            raise

    def process(self, directory=None, length_scale=None, noise_scale=None, noise_w=None) -> List[Path]:
        """
        Process all markdown files in the input directory.

        Args:
            directory: Optional override for input directory.
            length_scale: Optional speech speed override for all files
            noise_scale: Optional stability override for all files
            noise_w: Optional phoneme width override for all files

        Returns:
            List of paths to generated audio files.
        """
        directory = directory or self.input_dir
        input_files = sorted(list(Path(directory).glob("*.md")))

        output_files = []
        for input_file in input_files:
            output_file = self.synthesize_chunk(input_file, None, length_scale, noise_scale, noise_w)
            if output_file:
                output_files.append(output_file)

        logger.info(f"Processed {len(input_files)} files, generated {len(output_files)} audio files")
        return output_files


def process_markdown_file(file_path, output_dir, **kwargs) -> tuple[bool, str]:
    """
    Wrapper function to use Piper TTS generator instead of ElevenLabs.
    This matches the interface expected by the main pipeline.

    Args:
        file_path: Path to markdown file to process
        output_dir: Directory to save audio files
        **kwargs: Additional arguments (ignored for Piper)

    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        # Load config to get model settings
        try:
            import yaml
            with open("config.yaml", "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
            piper_config = config.get("tts", {}).get("piper", {})
            model_name = piper_config.get("model", "cs_CZ-jirka-medium")
            keep_wav = piper_config.get("keep_wav", True)  # Default to True for best quality
            upsample = piper_config.get("upsample", True)  # Default to True for better quality

            # Get synthesis parameters from config or kwargs
            length_scale = kwargs.get('length_scale', piper_config.get('length_scale', 1.0))
            noise_scale = kwargs.get('noise_scale', piper_config.get('noise_scale', 0.667))
            noise_w = kwargs.get('noise_w', piper_config.get('noise_w', 0.8))

            # Apply preset if specified
            preset = kwargs.get('preset')
        except Exception:
            # Fallback to default if config loading fails
            model_name = "cs_CZ-jirka-medium"
            keep_wav = True  # Default to WAV for maximum quality
            upsample = True
            length_scale = kwargs.get('length_scale', 1.0)
            noise_scale = kwargs.get('noise_scale', 0.667)
            noise_w = kwargs.get('noise_w', 0.8)
            preset = kwargs.get('preset')

        generator = PiperAudioChunkGenerator(
            input_dir=str(Path(file_path).parent),
            output_dir=str(output_dir),
            model_name=model_name,
            keep_wav=keep_wav,
            upsample=upsample,
            length_scale=length_scale,
            noise_scale=noise_scale,
            noise_w=noise_w
        )

        # Apply preset if specified
        if preset:
            generator.apply_preset(preset)
        result = generator.process()
        success = len(result) > 0
        message = f"Generated {len(result)} audio files with Piper" if success else "Failed to generate audio with Piper"
        return success, message
    except Exception as e:
        logger.error(f"Piper TTS processing failed: {e}")
        return False, f"Piper TTS error: {str(e)}"


if __name__ == "__main__":
    # Example usage
    import sys

    if len(sys.argv) != 3:
        print("Usage: python piper_audio_chunk_generator.py <input_dir> <output_dir>")
        sys.exit(1)

    input_dir = sys.argv[1]
    output_dir = sys.argv[2]

    try:
        generator = PiperAudioChunkGenerator(input_dir, output_dir)
        output_files = generator.process()
        print(f"Generated {len(output_files)} audio files")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
