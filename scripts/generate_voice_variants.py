#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Voice Variant Generation Script
Generate multiple audio variants using different models, engines, and parameters for comparison.
"""

import argparse
import json
import logging
import sys
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import yaml

# Add the project root to Python path so we can import modules
sys.path.insert(0, str(Path(__file__).parent.parent))

# TTS engines
try:
    from piper_audio_chunk_generator import PiperAudioChunkGenerator
    PIPER_AVAILABLE = True
except ImportError:
    PIPER_AVAILABLE = False

try:
    from coqui_audio_chunk_generator import CoquiAudioChunkGenerator
    COQUI_AVAILABLE = True
except ImportError:
    COQUI_AVAILABLE = False

try:
    from espeak_audio_chunk_generator import EspeakAudioChunkGenerator
    ESPEAK_AVAILABLE = True
except ImportError:
    ESPEAK_AVAILABLE = False

try:
    from audio_chunk_generator import process_markdown_file as elevenlabs_process
    ELEVENLABS_AVAILABLE = True
except ImportError:
    ELEVENLABS_AVAILABLE = False

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class VoiceVariantGenerator:
    """Generate multiple voice variants for comparison."""

    def __init__(self, output_base_dir: str = "data/5-audio-chunks/variants"):
        """
        Initialize the variant generator.

        Args:
            output_base_dir: Base directory for variant outputs
        """
        self.output_base_dir = Path(output_base_dir)
        self.output_base_dir.mkdir(parents=True, exist_ok=True)

        # Load configuration
        self.config = self._load_config()

        # Available TTS engines
        self.available_engines = self._check_available_engines()

        # Default parameter combinations for testing
        self.parameter_combinations = [
            {'preset': 'natural', 'length_scale': 1.0, 'noise_scale': 0.667, 'noise_w': 0.8},
            {'preset': 'clear', 'length_scale': 1.0, 'noise_scale': 0.5, 'noise_w': 0.7},
            {'preset': 'expressive', 'length_scale': 1.0, 'noise_scale': 0.8, 'noise_w': 0.9},
            {'preset': 'fast', 'length_scale': 1.2, 'noise_scale': 0.6, 'noise_w': 0.8},
            {'preset': 'slow', 'length_scale': 0.8, 'noise_scale': 0.5, 'noise_w': 0.7},
        ]

        # Czech voice models to test
        self.czech_models = [
            'cs_CZ-jirka-medium',
            'cs_CZ-jirka-low',
            # Add more if discovered
        ]

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from config.yaml."""
        config_path = Path("config.yaml")
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    return yaml.safe_load(f)
            except Exception as e:
                logger.warning(f"Failed to load config: {e}")

        return {}

    def _check_available_engines(self) -> List[str]:
        """Check which TTS engines are available."""
        engines = []

        # Check each engine by trying to import it
        try:
            from piper_audio_chunk_generator import PiperAudioChunkGenerator
            engines.append('piper')
            logger.debug("Piper import successful")
        except ImportError as e:
            logger.debug(f"Piper import failed: {e}")

        try:
            from coqui_audio_chunk_generator import CoquiAudioChunkGenerator
            engines.append('coqui')
            logger.debug("Coqui import successful")
        except ImportError as e:
            logger.debug(f"Coqui import failed: {e}")

        try:
            from espeak_audio_chunk_generator import EspeakAudioChunkGenerator
            engines.append('espeak')
            logger.debug("Espeak import successful")
        except ImportError as e:
            logger.debug(f"Espeak import failed: {e}")

        try:
            from audio_chunk_generator import process_markdown_file as elevenlabs_process
            engines.append('elevenlabs')
            logger.debug("ElevenLabs import successful")
        except ImportError as e:
            logger.debug(f"ElevenLabs import failed: {e}")

        logger.info(f"Available TTS engines: {', '.join(engines) if engines else 'none'}")
        return engines

    def generate_variants(self, input_file: str, mode: str = "all", engines: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Generate multiple voice variants for comparison.

        Args:
            input_file: Path to markdown file to process
            mode: Generation mode ('models', 'params', 'engines', 'all')
            engines: Optional list of engines to use (overrides mode)

        Returns:
            Dictionary with generation results and metadata
        """
        input_path = Path(input_file)
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_file}")

        # Get chapter name from input file
        chapter_name = input_path.stem.replace("-OPTIMIZED", "")
        chapter_dir = self.output_base_dir / chapter_name
        chapter_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Generating variants for {chapter_name} in mode: {mode}")

        # Debug: Check available engines
        logger.info(f"Available engines at generation time: {self.available_engines}")

        # Determine which variants to generate
        if engines:
            variants_to_generate = self._get_engine_variants(engines)
        else:
            variants_to_generate = self._get_mode_variants(mode)

        results = {
            'chapter': chapter_name,
            'input_file': str(input_path),
            'mode': mode,
            'timestamp': time.time(),
            'variants': []
        }

        total_variants = len(variants_to_generate)
        logger.info(f"Will generate {total_variants} variants")
        logger.info(f"Variants to generate: {[v['name'] for v in variants_to_generate]}")

        for i, variant in enumerate(variants_to_generate, 1):
            logger.info(f"Generating variant {i}/{total_variants}: {variant['name']}")

            try:
                result = self._generate_single_variant(input_path, variant, chapter_dir)
                if result:
                    results['variants'].append(result)
                    logger.info(f"✓ Generated: {variant['name']}")
                else:
                    logger.warning(f"✗ Failed: {variant['name']}")
            except Exception as e:
                logger.error(f"✗ Error generating {variant['name']}: {e}")
                results['variants'].append({
                    'name': variant['name'],
                    'success': False,
                    'error': str(e)
                })

        # Save results metadata
        self._save_metadata(results, chapter_dir)

        logger.info(f"Generated {len([v for v in results['variants'] if v.get('success', False)])}/{total_variants} variants successfully")
        return results

    def _get_mode_variants(self, mode: str) -> List[Dict[str, Any]]:
        """Get variants to generate based on mode."""
        variants = []

        if mode in ['models', 'all']:
            # Different Piper models
            for model in self.czech_models:
                if 'piper' in self.available_engines:
                    variants.append({
                        'name': f"piper_{model}_natural",
                        'engine': 'piper',
                        'model': model,
                        'preset': 'natural'
                    })

        if mode in ['params', 'all']:
            # Different parameter combinations with default model
            for params in self.parameter_combinations:
                if 'piper' in self.available_engines:
                    preset_name = params['preset']
                    variants.append({
                        'name': f"piper_cs_CZ-jirka-medium_{preset_name}",
                        'engine': 'piper',
                        'model': 'cs_CZ-jirka-medium',
                        'preset': preset_name,
                        'params': params
                    })

        if mode in ['engines', 'all']:
            # Different engines with default settings
            for engine in self.available_engines:
                variants.append({
                    'name': f"{engine}_default",
                    'engine': engine,
                    'model': self._get_default_model_for_engine(engine)
                })

        return variants

    def _get_engine_variants(self, engines: List[str]) -> List[Dict[str, Any]]:
        """Get variants for specific engines."""
        variants = []
        for engine in engines:
            if engine in self.available_engines:
                variants.append({
                    'name': f"{engine}_default",
                    'engine': engine,
                    'model': self._get_default_model_for_engine(engine)
                })
        return variants

    def _get_default_model_for_engine(self, engine: str) -> str:
        """Get default model for an engine."""
        defaults = {
            'piper': 'cs_CZ-jirka-medium',
            'coqui': 'tts_models/multilingual/multi-dataset/xtts_v2',
            'espeak': 'cs',
            'elevenlabs': 'OJtLHqR5g0hxcgc27j7C'  # Voice ID
        }
        return defaults.get(engine, '')

    def _generate_single_variant(self, input_path: Path, variant: Dict[str, Any], output_dir: Path) -> Optional[Dict[str, Any]]:
        """Generate a single voice variant."""
        engine = variant['engine']
        variant_name = variant['name']

        # Create unique output path for this variant
        output_file = output_dir / f"{variant_name}.wav"  # Default to WAV for best quality

        start_time = time.time()

        try:
            if engine == 'piper':
                success = self._generate_piper_variant(input_path, variant, output_file)
            elif engine == 'coqui':
                success = self._generate_coqui_variant(input_path, variant, output_file)
            elif engine == 'espeak':
                success = self._generate_espeak_variant(input_path, variant, output_file)
            elif engine == 'elevenlabs':
                success = self._generate_elevenlabs_variant(input_path, variant, output_file)
            else:
                logger.error(f"Unsupported engine: {engine}")
                return None

            if success and output_file.exists():
                # Get file metadata
                file_size = output_file.stat().st_size
                duration = self._get_audio_duration(output_file)

                return {
                    'name': variant_name,
                    'engine': engine,
                    'model': variant.get('model', ''),
                    'preset': variant.get('preset', ''),
                    'params': variant.get('params', {}),
                    'output_file': str(output_file),
                    'file_size_bytes': file_size,
                    'duration_seconds': duration,
                    'generation_time': time.time() - start_time,
                    'success': True
                }
            else:
                return None

        except Exception as e:
            logger.error(f"Failed to generate variant {variant_name}: {e}")
            return None

    def _generate_piper_variant(self, input_path: Path, variant: Dict[str, Any], output_file: Path) -> bool:
        """Generate variant using Piper TTS."""
        if not PIPER_AVAILABLE:
            return False

        try:
            # Create generator with specific settings
            model_name = variant.get('model', 'cs_CZ-jirka-medium')
            generator = PiperAudioChunkGenerator(
                input_dir=str(input_path.parent),
                output_dir=str(output_file.parent),
                model_name=model_name,
                keep_wav=True,  # Always use WAV for variants
                upsample=True
            )

            # Apply preset or parameters
            if 'preset' in variant:
                generator.apply_preset(variant['preset'])
            elif 'params' in variant:
                params = variant['params']
                generator.set_parameters(
                    length_scale=params.get('length_scale'),
                    noise_scale=params.get('noise_scale'),
                    noise_w=params.get('noise_w')
                )

            # Generate the audio
            result = generator.synthesize_chunk(input_path)

            # Move result to desired output location if needed
            if result and result != output_file:
                if output_file.exists():
                    output_file.unlink()
                result.rename(output_file)

            return output_file.exists()

        except Exception as e:
            logger.error(f"Piper variant generation failed: {e}")
            return False

    def _generate_coqui_variant(self, input_path: Path, variant: Dict[str, Any], output_file: Path) -> bool:
        """Generate variant using Coqui TTS."""
        if not COQUI_AVAILABLE:
            return False

        try:
            model_name = variant.get('model', 'tts_models/multilingual/multi-dataset/xtts_v2')
            generator = CoquiAudioChunkGenerator(
                input_dir=str(input_path.parent),
                output_dir=str(output_file.parent),
                model_name=model_name,
                language="cs"
            )

            result = generator.synthesize_chunk(input_path)
            if result and result != output_file:
                if output_file.exists():
                    output_file.unlink()
                result.rename(output_file)

            return output_file.exists()

        except Exception as e:
            logger.error(f"Coqui variant generation failed: {e}")
            return False

    def _generate_espeak_variant(self, input_path: Path, variant: Dict[str, Any], output_file: Path) -> bool:
        """Generate variant using eSpeak-ng."""
        if not ESPEAK_AVAILABLE:
            return False

        try:
            generator = EspeakAudioChunkGenerator(
                input_dir=str(input_path.parent),
                output_dir=str(output_file.parent),
                voice=variant.get('model', 'cs'),
                rate=175,  # Default Czech rate
                pitch=50,
                volume=100
            )

            result = generator.synthesize_chunk(input_path)
            if result and result != output_file:
                if output_file.exists():
                    output_file.unlink()
                result.rename(output_file)

            return output_file.exists()

        except Exception as e:
            logger.error(f"eSpeak variant generation failed: {e}")
            return False

    def _generate_elevenlabs_variant(self, input_path: Path, variant: Dict[str, Any], output_file: Path) -> bool:
        """Generate variant using ElevenLabs."""
        if not ELEVENLABS_AVAILABLE:
            return False

        try:
            # Convert WAV to MP3 for ElevenLabs output
            mp3_file = output_file.with_suffix('.mp3')

            # Get config settings
            elevenlabs_config = self.config.get('tts', {}).get('elevenlabs', {})
            voice_id = variant.get('model', elevenlabs_config.get('voice_id', 'OJtLHqR5g0hxcgc27j7C'))
            model_id = elevenlabs_config.get('model_id', 'eleven_multilingual_v2')

            success, message = elevenlabs_process(
                file_path=str(input_path),
                output_dir=str(output_file.parent),
                voice_id=voice_id,
                model_id=model_id,
                stability=elevenlabs_config.get('stability', 0.5),
                similarity_boost=elevenlabs_config.get('similarity_boost', 0.75),
                style=elevenlabs_config.get('style', 0.0)
            )

            if success:
                # Find the generated file and rename if needed
                generated_files = list(output_file.parent.glob("*.mp3"))
                if generated_files:
                    generated_file = generated_files[0]
                    if generated_file != mp3_file:
                        generated_file.rename(mp3_file)
                    # Convert MP3 to WAV for consistency
                    self._convert_mp3_to_wav(mp3_file, output_file)
                    return output_file.exists()

            return False

        except Exception as e:
            logger.error(f"ElevenLabs variant generation failed: {e}")
            return False

    def _convert_mp3_to_wav(self, mp3_file: Path, wav_file: Path):
        """Convert MP3 to WAV using ffmpeg."""
        import subprocess
        try:
            cmd = [
                "ffmpeg", "-i", str(mp3_file),
                "-acodec", "pcm_s16le",
                "-ar", "44100",
                "-ac", "1",
                str(wav_file), "-y"
            ]
            subprocess.run(cmd, check=True, capture_output=True)
            mp3_file.unlink()  # Remove original MP3
        except Exception as e:
            logger.warning(f"Failed to convert {mp3_file} to WAV: {e}")

    def _get_audio_duration(self, audio_file: Path) -> float:
        """Get audio file duration in seconds."""
        try:
            import subprocess
            cmd = [
                "ffprobe", "-v", "error", "-show_entries",
                "format=duration", "-of", "default=noprint_wrappers=1:nokey=1",
                str(audio_file)
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return float(result.stdout.strip())
        except Exception:
            return 0.0

    def _save_metadata(self, results: Dict[str, Any], output_dir: Path):
        """Save generation metadata to JSON file."""
        metadata_file = output_dir / "variants_metadata.json"
        try:
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved metadata to: {metadata_file}")
        except Exception as e:
            logger.error(f"Failed to save metadata: {e}")


def main():
    """Main entry point for voice variant generation script."""
    parser = argparse.ArgumentParser(
        description="Generate multiple voice variants for comparison",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/generate_voice_variants.py data/4-markdown-chunks-optimized/chapter_32b-OPTIMIZED.md
  python scripts/generate_voice_variants.py data/4-markdown-chunks-optimized/chapter_32b-OPTIMIZED.md --mode params
  python scripts/generate_voice_variants.py data/4-markdown-chunks-optimized/chapter_32b-OPTIMIZED.md --engines piper coqui
  python scripts/generate_voice_variants.py data/4-markdown-chunks-optimized/chapter_32b-OPTIMIZED.md --output custom_output_dir

Modes:
  models  - Different voice models (Piper Czech models)
  params  - Different parameter combinations
  engines - Different TTS engines with default settings
  all     - Comprehensive comparison (all modes combined)
        """
    )

    parser.add_argument(
        'input_file',
        help='Path to markdown file to generate variants for'
    )

    parser.add_argument(
        '--mode', '-m',
        choices=['models', 'params', 'engines', 'all'],
        default='all',
        help='Generation mode (default: all)'
    )

    parser.add_argument(
        '--engines', '-e',
        nargs='+',
        choices=['piper', 'coqui', 'espeak', 'elevenlabs'],
        help='Specific engines to use (overrides mode)'
    )

    parser.add_argument(
        '--output', '-o',
        default='data/5-audio-chunks/variants',
        help='Output base directory (default: data/5-audio-chunks/variants)'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        generator = VoiceVariantGenerator(args.output)
        results = generator.generate_variants(args.input_file, args.mode, args.engines)

        print("\n✓ Variant generation completed!")
        print(f"Generated {len([v for v in results['variants'] if v.get('success')])} variants")
        print(f"Output directory: {args.output}/{results['chapter']}")

        # Show summary
        successful_variants = [v for v in results['variants'] if v.get('success')]
        if successful_variants:
            print("\nGenerated variants:")
            for variant in successful_variants:
                duration = variant.get('duration_seconds', 0)
                size_mb = variant.get('file_size_bytes', 0) / (1024 * 1024)
                print(f"  - {variant['name']}: {duration:.1f}s, {size_mb:.1f}MB")

    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
