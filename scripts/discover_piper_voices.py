#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Piper Voice Model Discovery and Download Script
Query HuggingFace for available Piper models and download them automatically.
"""

import argparse
import json
import logging
import os
import shutil
from pathlib import Path
from typing import Dict, List, Any, Optional
import yaml

# Add project root to Python path to enable imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

# Reuse the PiperVoiceLister from list_piper_voices.py
from scripts.list_piper_voices import PiperVoiceLister

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class PiperVoiceDiscoverer:
    """Discover and download Piper voice models automatically."""

    def __init__(self):
        self.lister = PiperVoiceLister()
        self.models_dir = Path.home() / ".piper" / "models"

        # Load config to get preferred models
        self.config = self._load_config()
        self.preferred_models = self.config.get('voice_variants', {}).get('models_to_test', [])

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

    def discover_and_download(self, language_filter: Optional[str] = None, download_all: bool = False) -> List[Dict]:
        """
        Discover available models and download missing ones.

        Args:
            language_filter: Optional language code to filter (e.g., 'cs')
            download_all: If True, download all models; if False, only preferred ones

        Returns:
            List of downloaded model information
        """
        logger.info("Discovering available Piper voice models...")

        # Get available models
        available_models = self.lister.list_models(language_filter=language_filter, use_cache=False)

        if not available_models:
            logger.warning("No models found")
            return []

        # Filter models to download
        if download_all:
            models_to_download = available_models
            logger.info(f"Will download all {len(models_to_download)} models")
        else:
            # Download preferred models or all Czech models if no preference set
            if self.preferred_models:
                models_to_download = [m for m in available_models if m.get('model_name') in self.preferred_models]
                logger.info(f"Will download {len(models_to_download)} preferred models: {', '.join(self.preferred_models)}")
            elif language_filter:
                models_to_download = available_models
                logger.info(f"Will download all {len(models_to_download)} {language_filter.upper()} models")
            else:
                models_to_download = available_models[:5]  # Download first 5 as examples
                logger.info(f"Will download first {len(models_to_download)} models as examples")

        downloaded_models = []

        for model_info in models_to_download:
            model_name = model_info.get('model_name', '')
            if self._is_model_downloaded(model_name):
                logger.info(f"Model {model_name} already downloaded, skipping")
                downloaded_models.append(model_info)
                continue

            logger.info(f"Downloading model: {model_name}")
            try:
                self._download_model(model_info)
                downloaded_models.append(model_info)
                logger.info(f"✓ Successfully downloaded: {model_name}")
            except Exception as e:
                logger.error(f"✗ Failed to download {model_name}: {e}")

        logger.info(f"Downloaded {len(downloaded_models)}/{len(models_to_download)} models")
        return downloaded_models

    def _is_model_downloaded(self, model_name: str) -> bool:
        """Check if a model is already downloaded."""
        model_file = self.models_dir / f"{model_name}.onnx"
        config_file = self.models_dir / f"{model_name}.onnx.json"
        return model_file.exists() and config_file.exists()

    def _download_model(self, model_info: Dict[str, Any]):
        """Download a specific model."""
        model_name = model_info.get('model_name', '')
        download_url = model_info.get('download_url', '')
        config_url = model_info.get('config_url', '')

        if not download_url or not config_url:
            raise ValueError(f"Missing download URLs for model {model_name}")

        # Ensure models directory exists
        self.models_dir.mkdir(parents=True, exist_ok=True)

        model_file = self.models_dir / f"{model_name}.onnx"
        config_file = self.models_dir / f"{model_name}.onnx.json"

        # Download model file
        logger.info(f"Downloading model file: {model_name}.onnx")
        self._download_file(download_url, model_file)

        # Download config file
        logger.info(f"Downloading config file: {model_name}.onnx.json")
        self._download_file(config_url, config_file)

        # Verify files
        if not model_file.exists() or model_file.stat().st_size == 0:
            raise FileNotFoundError(f"Model file download failed: {model_file}")
        if not config_file.exists() or config_file.stat().st_size == 0:
            raise FileNotFoundError(f"Config file download failed: {config_file}")

    def _download_file(self, url: str, dest_path: Path):
        """Download a file with progress indication."""
        try:
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
                            print(f"\rDownloading: {progress:.1f}%", end='', flush=True)

            print()  # New line after progress

        except ImportError:
            # Fallback to urllib if requests not available
            import urllib.request

            def progress_hook(blocks, block_size, total_size):
                if total_size > 0:
                    downloaded = blocks * block_size
                    progress = (downloaded / total_size) * 100
                    print(f"\rDownloading: {progress:.1f}%", end='', flush=True)

            urllib.request.urlretrieve(url, dest_path, progress_hook)
            print()

    def list_downloaded_models(self) -> List[str]:
        """List all downloaded models."""
        if not self.models_dir.exists():
            return []

        models = []
        for file_path in self.models_dir.glob("*.onnx"):
            if file_path.with_suffix('.onnx.json').exists():
                models.append(file_path.stem)

        return sorted(models)

    def cleanup_unused_models(self, keep_models: Optional[List[str]] = None) -> int:
        """
        Remove unused model files.

        Args:
            keep_models: List of model names to keep (if None, keep preferred models)

        Returns:
            Number of models removed
        """
        if keep_models is None:
            keep_models = self.preferred_models

        downloaded_models = self.list_downloaded_models()
        models_to_remove = [m for m in downloaded_models if m not in keep_models]

        removed_count = 0
        for model_name in models_to_remove:
            try:
                model_file = self.models_dir / f"{model_name}.onnx"
                config_file = self.models_dir / f"{model_name}.onnx.json"

                if model_file.exists():
                    model_file.unlink()
                if config_file.exists():
                    config_file.unlink()

                logger.info(f"Removed unused model: {model_name}")
                removed_count += 1
            except Exception as e:
                logger.warning(f"Failed to remove model {model_name}: {e}")

        return removed_count

    def ensure_preferred_models(self) -> List[str]:
        """
        Ensure all preferred models are downloaded.

        Returns:
            List of downloaded model names
        """
        logger.info("Ensuring preferred models are downloaded...")

        downloaded = self.discover_and_download(download_all=False)
        return [m.get('model_name', '') for m in downloaded if m.get('model_name')]


def main():
    parser = argparse.ArgumentParser(
        description="Discover and download Piper voice models",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/discover_piper_voices.py                    # Download preferred Czech models
  python scripts/discover_piper_voices.py --language cs     # Download all Czech models
  python scripts/discover_piper_voices.py --all             # Download all available models
  python scripts/discover_piper_voices.py --list            # List downloaded models
  python scripts/discover_piper_voices.py --cleanup         # Remove unused models
        """
    )

    parser.add_argument(
        '--language', '-l',
        type=str,
        help='Language code to filter models (e.g., cs for Czech)'
    )

    parser.add_argument(
        '--all', '-a',
        action='store_true',
        help='Download all available models (use with caution)'
    )

    parser.add_argument(
        '--list',
        action='store_true',
        help='List currently downloaded models'
    )

    parser.add_argument(
        '--cleanup',
        action='store_true',
        help='Remove unused model files'
    )

    parser.add_argument(
        '--refresh',
        action='store_true',
        help='Force refresh model list from HuggingFace'
    )

    args = parser.parse_args()

    try:
        discoverer = PiperVoiceDiscoverer()

        if args.list:
            # List downloaded models
            downloaded = discoverer.list_downloaded_models()
            if downloaded:
                print("Downloaded Piper models:")
                for model in downloaded:
                    print(f"  - {model}")
                print(f"\nTotal: {len(downloaded)} models")
            else:
                print("No Piper models downloaded yet.")
                print("Run without --list to download preferred models.")

        elif args.cleanup:
            # Clean up unused models
            removed = discoverer.cleanup_unused_models()
            print(f"Removed {removed} unused models")

        else:
            # Discover and download models
            downloaded = discoverer.discover_and_download(
                language_filter=args.language,
                download_all=args.all
            )

            print(f"\n✓ Downloaded {len(downloaded)} models")
            if downloaded:
                print("Downloaded models:")
                for model in downloaded:
                    model_name = model.get('model_name', 'Unknown')
                    print(f"  - {model_name}")

    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
    except Exception as e:
        logger.error(f"Error: {e}")
        exit(1)


if __name__ == "__main__":
    main()
