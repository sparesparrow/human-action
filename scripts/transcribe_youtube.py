#!/usr/bin/env python3
"""
YouTube Transcription CLI Wrapper for Human Action Project

This script provides a CLI interface for transcribing YouTube videos
using the integrated transcription module.
"""

import argparse
import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from transcribe import TranscriptionPipeline


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Transcribe YouTube videos using OpenAI Whisper',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/transcribe_youtube.py "https://www.youtube.com/watch?v=VIDEO_ID"
  python scripts/transcribe_youtube.py "URL" --config transcribe/config.yaml --model medium
  python scripts/transcribe_youtube.py "URL" --formats txt,srt --output ./my-transcripts
  python scripts/transcribe_youtube.py "URL" --translate --tts --video
        """
    )

    parser.add_argument('url', help='YouTube URL to transcribe')
    parser.add_argument('--config', '-c', default='transcribe/config.yaml',
                       help='Path to config file (default: transcribe/config.yaml)')
    parser.add_argument('--output', '-o', help='Output directory override')
    parser.add_argument('--model', '-m',
                       choices=['tiny', 'base', 'small', 'medium', 'large'],
                       help='Whisper model size')
    parser.add_argument('--formats', '-f',
                       help='Output formats: txt,srt,json,vtt (default: all)')
    parser.add_argument('--device', '-d',
                       choices=['cpu', 'cuda'],
                       help='Device for Whisper (default: cpu)')

    # Optional features
    parser.add_argument('--translate', action='store_true',
                       help='Translate transcript to Czech')
    parser.add_argument('--tts', action='store_true',
                       help='Generate Czech TTS audio')
    parser.add_argument('--video', action='store_true',
                       help='Create video with Czech audio')

    # TTS options
    parser.add_argument('--tts-voice', default='cs-CZ-AntoninNeural',
                       help='TTS voice (default: cs-CZ-AntoninNeural)')
    parser.add_argument('--tts-rate', default='+0%',
                       help='TTS speech rate (default: +0%)')
    parser.add_argument('--tts-volume', default='+0%',
                       help='TTS volume (default: +0%)')

    args = parser.parse_args()

    try:
        # Create pipeline with config
        pipeline = TranscriptionPipeline(args.config)

        # Override config with CLI arguments
        if args.output:
            pipeline.config['output']['directory'] = args.output
        if args.model:
            pipeline.config['whisper']['model'] = args.model
        if args.device:
            pipeline.config['whisper']['device'] = args.device
        if args.formats:
            formats = [f.strip() for f in args.formats.split(',')]
            valid_formats = {'txt', 'srt', 'json', 'vtt'}
            invalid = set(formats) - valid_formats
            if invalid:
                print(f"Warning: Invalid formats ignored: {', '.join(invalid)}")
            pipeline.config['output']['formats'] = [f for f in formats if f in valid_formats]

        # Set optional features
        if args.translate:
            pipeline.config['translation']['enabled'] = True
        if args.tts:
            pipeline.config['tts']['enabled'] = True
        if args.video:
            pipeline.config['video']['enabled'] = True

        # Set TTS options
        if args.tts_voice:
            pipeline.config['tts']['voice'] = args.tts_voice
        if args.tts_rate:
            pipeline.config['tts']['rate'] = args.tts_rate
        if args.tts_volume:
            pipeline.config['tts']['volume'] = args.tts_volume

        # Run transcription
        print(f"🎬 Starting transcription of: {args.url}")
        output_dir = pipeline.run(args.url)

        print(f"✅ Transcription completed successfully!")
        print(f"📁 Output directory: {output_dir}")

        # List generated files
        if os.path.exists(output_dir):
            print("\n📄 Generated files:")
            for file in sorted(Path(output_dir).glob("*")):
                if file.is_file():
                    print(f"  - {file.name}")

    except KeyboardInterrupt:
        print("\n\n❌ Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
