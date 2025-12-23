#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
List Available Piper Voice Models
Query HuggingFace Piper voices repository for available models and display Czech models.
"""

import argparse
import json
import logging
import requests
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class PiperVoiceLister:
    """List and analyze available Piper voice models."""

    def __init__(self):
        self.base_url = "https://huggingface.co/api/models"
        self.piper_voices_org = "rhasspy/piper-voices"
        self.cache_file = Path("data/voice_models/available_piper_models.json")

    def query_piper_repository(self, language_filter: Optional[str] = None) -> List[Dict]:
        """
        Query Piper voices repository directly for available models.

        Args:
            language_filter: Optional language code to filter results (e.g., 'cs' for Czech)

        Returns:
            List of model metadata dictionaries
        """
        try:
            logger.info("Querying Piper voices repository structure...")

            # Get all language directories
            base_url = "https://huggingface.co/api/models/rhasspy/piper-voices/tree/main"
            response = requests.get(base_url)
            response.raise_for_status()

            languages = []
            for item in response.json():
                if item.get('type') == 'directory' and len(item['path']) == 2:  # Language codes are 2 chars
                    languages.append(item['path'])

            logger.info(f"Found languages: {', '.join(languages)}")

            all_models = []

            # Process each language
            for lang in languages:
                if language_filter and lang != language_filter:
                    continue

                logger.info(f"Processing language: {lang}")
                lang_models = self._get_models_for_language(lang)
                all_models.extend(lang_models)

            logger.info(f"Found {len(all_models)} total models")
            return all_models

        except requests.RequestException as e:
            logger.error(f"Failed to query Piper repository: {e}")
            return []

    def _get_models_for_language(self, language: str) -> List[Dict]:
        """
        Get all models for a specific language.

        Args:
            language: Language code (e.g., 'cs', 'en')

        Returns:
            List of model metadata for that language
        """
        models = []

        try:
            # Get language directory contents
            lang_url = f"https://huggingface.co/api/models/rhasspy/piper-voices/tree/main/{language}"
            response = requests.get(lang_url)
            response.raise_for_status()

            for item in response.json():
                if item.get('type') == 'directory':
                    # This should be lang_country (e.g., cs_CZ, en_US)
                    lang_country = item['path'].split('/')[-1]
                    country_models = self._get_models_for_lang_country(language, lang_country)
                    models.extend(country_models)

        except requests.RequestException as e:
            logger.warning(f"Failed to get models for language {language}: {e}")

        return models

    def _get_models_for_lang_country(self, language: str, lang_country: str) -> List[Dict]:
        """
        Get all models for a specific language-country combination.

        Args:
            language: Language code (e.g., 'cs')
            lang_country: Language-country code (e.g., 'cs_CZ')

        Returns:
            List of model metadata
        """
        models = []

        try:
            # Get lang_country directory contents
            lc_url = f"https://huggingface.co/api/models/rhasspy/piper-voices/tree/main/{language}/{lang_country}"
            response = requests.get(lc_url)
            response.raise_for_status()

            for item in response.json():
                if item.get('type') == 'directory':
                    # This should be speaker name (e.g., jirka, alan)
                    speaker = item['path'].split('/')[-1]
                    speaker_models = self._get_models_for_speaker(language, lang_country, speaker)
                    models.extend(speaker_models)

        except requests.RequestException as e:
            logger.warning(f"Failed to get models for {lang_country}: {e}")

        return models

    def _get_models_for_speaker(self, language: str, lang_country: str, speaker: str) -> List[Dict]:
        """
        Get all models for a specific speaker.

        Args:
            language: Language code (e.g., 'cs')
            lang_country: Language-country code (e.g., 'cs_CZ')
            speaker: Speaker name (e.g., 'jirka')

        Returns:
            List of model metadata
        """
        models = []

        try:
            # Get speaker directory contents
            speaker_url = f"https://huggingface.co/api/models/rhasspy/piper-voices/tree/main/{language}/{lang_country}/{speaker}"
            response = requests.get(speaker_url)
            response.raise_for_status()

            for item in response.json():
                if item.get('type') == 'directory':
                    # This should be quality level (e.g., medium, high, low)
                    quality = item['path'].split('/')[-1]
                    model_info = self._get_model_info(language, lang_country, speaker, quality)
                    if model_info:
                        models.append(model_info)

        except requests.RequestException as e:
            logger.warning(f"Failed to get models for speaker {speaker}: {e}")

        return models

    def _get_model_info(self, language: str, lang_country: str, speaker: str, quality: str) -> Optional[Dict]:
        """
        Get detailed information for a specific model.

        Args:
            language: Language code (e.g., 'cs')
            lang_country: Language-country code (e.g., 'cs_CZ')
            speaker: Speaker name (e.g., 'jirka')
            quality: Quality level (e.g., 'medium')

        Returns:
            Model metadata dictionary or None if not found
        """
        try:
            # Construct model name
            model_name = f"{lang_country}-{speaker}-{quality}"

            # Get model directory contents
            model_url = f"https://huggingface.co/api/models/rhasspy/piper-voices/tree/main/{language}/{lang_country}/{speaker}/{quality}"
            response = requests.get(model_url)
            response.raise_for_status()

            model_files = response.json()

            # Find the .onnx file
            onnx_file = None
            config_file = None
            for item in model_files:
                if item.get('type') == 'file' and item['path'].endswith('.onnx'):
                    onnx_file = item
                elif item.get('type') == 'file' and item['path'].endswith('.onnx.json'):
                    config_file = item

            if not onnx_file:
                return None

            # Get file size (may be in LFS info)
            size_mb = 0
            if 'lfs' in onnx_file:
                size_mb = onnx_file['lfs']['size'] // (1024 * 1024)  # Convert to MB
            elif 'size' in onnx_file:
                size_mb = onnx_file['size'] // (1024 * 1024)

            # Construct download URLs
            model_path = f"{language}/{lang_country}/{speaker}/{quality}"
            download_url = f"https://huggingface.co/rhasspy/piper-voices/resolve/main/{model_path}/{model_name}.onnx"
            config_url = f"https://huggingface.co/rhasspy/piper-voices/resolve/main/{model_path}/{model_name}.onnx.json"

            return {
                'model_id': f"rhasspy/piper-voices/{model_path}",
                'model_name': model_name,
                'language': language,
                'lang_country': lang_country,
                'speaker': speaker,
                'quality': quality,
                'size_mb': size_mb,
                'downloads': 0,  # Not available from this API
                'likes': 0,      # Not available from this API
                'last_modified': '',
                'tags': [],
                'pipeline_tag': 'text-to-speech',
                'model_url': f"https://huggingface.co/rhasspy/piper-voices/tree/main/{model_path}",
                'download_url': download_url,
                'config_url': config_url
            }

        except requests.RequestException as e:
            logger.warning(f"Failed to get model info for {lang_country}-{speaker}-{quality}: {e}")
            return None

    def parse_model_info(self, model_data: Dict) -> Dict[str, Any]:
        """
        Parse model metadata to extract useful information.

        Args:
            model_data: Raw model data from HuggingFace API

        Returns:
            Parsed model information
        """
        model_id = model_data.get('id', '')
        parts = model_id.split('/')

        if len(parts) < 5:
            return {}

        # Extract model components
        # Format: rhasspy/piper-voices/{lang}/{lang_country}/{speaker}/{quality}/{model_name}
        try:
            language = parts[3]
            lang_country = parts[4]
            speaker = parts[5] if len(parts) > 5 else ""
            quality = parts[6] if len(parts) > 6 else ""
            model_name = parts[-1] if len(parts) > 7 else lang_country

            return {
                'model_id': model_id,
                'model_name': model_name,
                'language': language,
                'lang_country': lang_country,
                'speaker': speaker,
                'quality': quality,
                'downloads': model_data.get('downloads', 0),
                'likes': model_data.get('likes', 0),
                'last_modified': model_data.get('lastModified', ''),
                'tags': model_data.get('tags', []),
                'pipeline_tag': model_data.get('pipeline_tag', ''),
                'model_url': f"https://huggingface.co/{model_id}",
                'download_url': f"https://huggingface.co/{model_id}/resolve/main/{model_name}.onnx",
                'config_url': f"https://huggingface.co/{model_id}/resolve/main/{model_name}.onnx.json"
            }
        except IndexError:
            logger.warning(f"Could not parse model path: {model_id}")
            return {}

    def get_model_sizes(self) -> Dict[str, int]:
        """
        Get approximate model file sizes (in MB) for known models.
        This is a fallback since the API doesn't provide file sizes directly.

        Returns:
            Dict mapping model names to approximate sizes in MB
        """
        # Common Piper model sizes (approximate)
        model_sizes = {
            'cs_CZ-jirka-medium': 45,
            'cs_CZ-jirka-high': 65,
            'cs_CZ-jirka-low': 25,
            'cs_CZ-jirka-x_low': 15,
            'en_US-lessac-medium': 45,
            'en_US-lessac-high': 65,
            'en_GB-alan-medium': 45,
            'en_GB-alan-high': 65,
            'de_DE-thorsten-medium': 45,
            'de_DE-thorsten-high': 65,
            'fr_FR-siwis-medium': 45,
            'fr_FR-siwis-high': 65,
            'es_ES-carlfm-x_low': 15,
            'es_ES-mls_9972-low': 25,
            'it_IT-riccardo-x_low': 15,
            'pt_BR-faber-medium': 45,
            'ru_RU-irina-medium': 45,
            'pl_PL-gosia-medium': 45,
            'uk_UA-ukrainian_tts-medium': 45,
            'ar_JO-kareem-medium': 45,
            'ca_ES-upc_ona-medium': 45,
            'da_DK-talesyntese-medium': 45,
            'hu_HU-anna-medium': 45,
            'ko_KR-ryan-medium': 45,
            'nl_NL-mls_5809-low': 25,
            'sv_SE-nst-medium': 45,
            'tt_TT-halid-medium': 45,
            'vi_VN-25hours-single-low': 25,
            'zh_CN-huayan-medium': 45,
            'ja_JP-kokoro-medium': 45,
            'fi_FI-harri-medium': 45,
            'tr_TR-dfki-medium': 45,
            'kk_KK-iseke-medium': 45,
            'ne_NP-google-medium': 45,
            'te_TE-cobalt-medium': 45,
            'sw_CD-lanfrica-medium': 45,
            'yo_NG-dauda-medium': 45,
            'ha_NE-koydirat-medium': 45,
        }
        return model_sizes

    def display_models_table(self, models: List[Dict], language_filter: Optional[str] = None):
        """
        Display models in a formatted table.

        Args:
            models: List of parsed model information
            language_filter: Language filter applied
        """
        if not models:
            print("No models found.")
            return

        print(f"\n{'='*80}")
        if language_filter:
            print(f"Available Piper Voice Models for {language_filter.upper()}")
        else:
            print("Available Piper Voice Models")
        print(f"{'='*80}")

        print(f"{'Model Name':<25} {'Language':<10} {'Quality':<8} {'Size':<6} {'Speaker':<10}")
        print("-" * 80)

        for model in sorted(models, key=lambda x: (x.get('language', ''), x.get('model_name', ''))):
            model_name = model.get('model_name', 'Unknown')
            language = model.get('language', 'Unknown')
            quality = model.get('quality', 'medium')
            size_mb = model.get('size_mb', 0)
            speaker = model.get('speaker', 'Unknown')

            print(f"{model_name:<25} {language:<10} {quality:<8} {size_mb:<6}MB {speaker:<10}")

        print(f"{'='*80}")
        print(f"Total models: {len(models)}")

        # Show unique languages
        languages = set(model.get('language') for model in models if model.get('language'))
        print(f"Languages: {', '.join(sorted(languages))}")

        # Show unique speakers and qualities
        speakers = set(model.get('speaker') for model in models if model.get('speaker'))
        qualities = set(model.get('quality') for model in models if model.get('quality'))

        if speakers:
            print(f"Speakers: {', '.join(sorted(speakers))}")
        if qualities:
            print(f"Quality levels: {', '.join(sorted(qualities))}")

    def save_to_cache(self, models: List[Dict]):
        """
        Save model list to cache file.

        Args:
            models: List of parsed model information
        """
        try:
            cache_data = {
                'timestamp': str(Path(__file__).stat().st_mtime),
                'models': models
            }

            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)

            logger.info(f"Saved {len(models)} models to cache: {self.cache_file}")

        except Exception as e:
            logger.error(f"Failed to save cache: {e}")

    def load_from_cache(self) -> Optional[List[Dict]]:
        """
        Load model list from cache file.

        Returns:
            Cached models if available, None otherwise
        """
        if not self.cache_file.exists():
            return None

        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
                return cache_data.get('models', [])
        except Exception as e:
            logger.warning(f"Failed to load cache: {e}")
            return None

    def list_models(self, language_filter: Optional[str] = None, use_cache: bool = True, force_refresh: bool = False) -> List[Dict]:
        """
        Main method to list available Piper voice models.

        Args:
            language_filter: Optional language code to filter results
            use_cache: Whether to use cached results
            force_refresh: Force refresh from repository even if cache exists

        Returns:
            List of parsed model information
        """
        # Try cache first
        if use_cache and not force_refresh:
            cached_models = self.load_from_cache()
            if cached_models:
                logger.info(f"Using cached data with {len(cached_models)} models")
                if language_filter:
                    cached_models = [m for m in cached_models if m.get('language') == language_filter]
                return cached_models

        # Query repository structure
        models = self.query_piper_repository(language_filter)

        # Save to cache
        self.save_to_cache(models)

        return models


def main():
    parser = argparse.ArgumentParser(
        description="List available Piper voice models",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/list_piper_voices.py                    # List all models
  python scripts/list_piper_voices.py --language cs     # List Czech models only
  python scripts/list_piper_voices.py --refresh         # Force refresh from API
  python scripts/list_piper_voices.py --no-cache        # Don't use cache
        """
    )

    parser.add_argument(
        '--language', '-l',
        type=str,
        help='Filter by language code (e.g., cs for Czech, en for English)'
    )

    parser.add_argument(
        '--refresh', '-r',
        action='store_true',
        help='Force refresh from HuggingFace API (ignore cache)'
    )

    parser.add_argument(
        '--no-cache',
        action='store_true',
        help='Do not use cached results'
    )

    parser.add_argument(
        '--json',
        action='store_true',
        help='Output results as JSON instead of table'
    )

    args = parser.parse_args()

    try:
        lister = PiperVoiceLister()
        models = lister.list_models(
            language_filter=args.language,
            use_cache=not args.no_cache,
            force_refresh=args.refresh
        )

        if args.json:
            print(json.dumps(models, indent=2, ensure_ascii=False))
        else:
            lister.display_models_table(models, args.language)

    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
