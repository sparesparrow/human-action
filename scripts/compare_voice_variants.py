#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Voice Variant Comparison Tool
Compare generated voice variants with audio players and metadata analysis.
"""

import argparse
import csv
import json
import logging
import os
import webbrowser
from pathlib import Path
from typing import Dict, List, Any, Optional
import yaml

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class VoiceVariantComparer:
    """Compare and analyze voice variants."""

    def __init__(self, variants_dir: str = "data/5-audio-chunks/variants"):
        """
        Initialize the comparer.

        Args:
            variants_dir: Directory containing variant outputs
        """
        self.variants_dir = Path(variants_dir)
        self.variants_dir.mkdir(parents=True, exist_ok=True)

    def compare_chapter(self, chapter_name: str, output_html: bool = True, open_browser: bool = False) -> Dict[str, Any]:
        """
        Compare variants for a specific chapter.

        Args:
            chapter_name: Name of the chapter to compare
            output_html: Generate HTML comparison page
            open_browser: Open HTML page in browser

        Returns:
            Comparison results dictionary
        """
        chapter_dir = self.variants_dir / chapter_name
        if not chapter_dir.exists():
            raise FileNotFoundError(f"Chapter directory not found: {chapter_dir}")

        # Load metadata
        metadata_file = chapter_dir / "variants_metadata.json"
        if not metadata_file.exists():
            raise FileNotFoundError(f"Metadata file not found: {metadata_file}")

        with open(metadata_file, 'r', encoding='utf-8') as f:
            metadata = json.load(f)

        variants = metadata.get('variants', [])

        # Filter successful variants
        successful_variants = [v for v in variants if v.get('success', False)]

        if not successful_variants:
            logger.warning(f"No successful variants found for {chapter_name}")
            return {}

        logger.info(f"Comparing {len(successful_variants)} variants for {chapter_name}")

        # Analyze variants
        analysis = self._analyze_variants(successful_variants, chapter_dir)

        # Generate reports
        if output_html:
            html_file = self._generate_html_report(metadata, analysis, chapter_dir)
            logger.info(f"Generated HTML report: {html_file}")

            if open_browser:
                webbrowser.open(f"file://{html_file}")

        # Export CSV report
        csv_file = self._export_csv_report(metadata, analysis, chapter_dir)
        logger.info(f"Generated CSV report: {csv_file}")

        return {
            'chapter': chapter_name,
            'metadata': metadata,
            'analysis': analysis,
            'html_report': str(html_file) if output_html else None,
            'csv_report': str(csv_file)
        }

    def _analyze_variants(self, variants: List[Dict], chapter_dir: Path) -> Dict[str, Any]:
        """Analyze variant metadata and generate comparison metrics."""
        analysis = {
            'total_variants': len(variants),
            'engines_used': set(),
            'models_used': set(),
            'quality_metrics': {},
            'size_comparison': {},
            'duration_comparison': {}
        }

        # Collect metrics
        for variant in variants:
            engine = variant.get('engine', 'unknown')
            model = variant.get('model', 'unknown')
            duration = variant.get('duration_seconds', 0)
            size_mb = variant.get('file_size_bytes', 0) / (1024 * 1024)

            analysis['engines_used'].add(engine)
            analysis['models_used'].add(model)

            # Size comparison
            analysis['size_comparison'][variant['name']] = size_mb

            # Duration comparison
            analysis['duration_comparison'][variant['name']] = duration

        # Convert sets to lists for JSON serialization
        analysis['engines_used'] = sorted(list(analysis['engines_used']))
        analysis['models_used'] = sorted(list(analysis['models_used']))

        # Calculate averages and ranges
        if analysis['size_comparison']:
            sizes = list(analysis['size_comparison'].values())
            analysis['size_stats'] = {
                'min': min(sizes),
                'max': max(sizes),
                'avg': sum(sizes) / len(sizes),
                'range': max(sizes) - min(sizes)
            }

        if analysis['duration_comparison']:
            durations = list(analysis['duration_comparison'].values())
            analysis['duration_stats'] = {
                'min': min(durations),
                'max': max(durations),
                'avg': sum(durations) / len(durations),
                'range': max(durations) - min(durations)
            }

        return analysis

    def _generate_html_report(self, metadata: Dict, analysis: Dict, chapter_dir: Path) -> Path:
        """Generate HTML comparison report with audio players."""
        chapter_name = metadata.get('chapter', 'unknown')
        html_file = chapter_dir / f"{chapter_name}_comparison.html"

        variants = [v for v in metadata.get('variants', []) if v.get('success', False)]

        # Sort variants by name for consistent display
        variants.sort(key=lambda x: x['name'])

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Voice Variants Comparison - {chapter_name}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        .header {{
            background: #2c3e50;
            color: white;
            padding: 20px;
            text-align: center;
        }}
        .summary {{
            padding: 20px;
            background: #ecf0f1;
            border-bottom: 1px solid #bdc3c7;
        }}
        .variants {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 20px;
            padding: 20px;
        }}
        .variant {{
            border: 1px solid #ddd;
            border-radius: 8px;
            padding: 15px;
            background: #fafafa;
        }}
        .variant h3 {{
            margin-top: 0;
            color: #2c3e50;
            font-size: 1.1em;
        }}
        .audio-player {{
            width: 100%;
            margin: 10px 0;
        }}
        .metadata {{
            font-size: 0.9em;
            color: #666;
            margin: 10px 0;
        }}
        .metadata div {{
            margin: 5px 0;
        }}
        .stats {{
            padding: 20px;
            background: #f8f9fa;
            border-top: 1px solid #dee2e6;
        }}
        .stats h3 {{
            margin-top: 0;
            color: #495057;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 10px 0;
        }}
        th, td {{
            padding: 8px 12px;
            text-align: left;
            border-bottom: 1px solid #dee2e6;
        }}
        th {{
            background: #e9ecef;
            font-weight: 600;
        }}
        .metric {{
            display: inline-block;
            background: #007bff;
            color: white;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 0.8em;
            margin: 2px;
        }}
        .badge {{
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.8em;
            font-weight: 500;
        }}
        .badge.engine-piper {{ background: #28a745; color: white; }}
        .badge.engine-coqui {{ background: #007bff; color: white; }}
        .badge.engine-espeak {{ background: #6c757d; color: white; }}
        .badge.engine-elevenlabs {{ background: #dc3545; color: white; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Voice Variants Comparison</h1>
            <h2>{chapter_name}</h2>
            <p>Generated on {metadata.get('timestamp', 'Unknown')}</p>
        </div>

        <div class="summary">
            <h3>Summary</h3>
            <p><strong>Total Variants:</strong> {analysis['total_variants']}</p>
            <p><strong>Engines Used:</strong> {', '.join(analysis['engines_used'])}</p>
            <p><strong>Models Used:</strong> {', '.join(analysis['models_used'])}</p>
        </div>

        <div class="variants">
"""

        # Add variant players
        for variant in variants:
            variant_name = variant['name']
            audio_file = Path(variant['output_file'])
            relative_path = audio_file.relative_to(chapter_dir) if audio_file.is_absolute() else audio_file

            engine = variant.get('engine', 'unknown')
            model = variant.get('model', 'unknown')
            duration = variant.get('duration_seconds', 0)
            size_mb = variant.get('file_size_bytes', 0) / (1024 * 1024)

            html_content += f"""
            <div class="variant">
                <h3>{variant_name}</h3>
                <span class="badge badge-engine-{engine}">{engine.upper()}</span>
                <audio class="audio-player" controls>
                    <source src="{relative_path}" type="audio/wav">
                    Your browser does not support the audio element.
                </audio>
                <div class="metadata">
                    <div><strong>Model:</strong> {model}</div>
                    <div><strong>Duration:</strong> {duration:.1f}s</div>
                    <div><strong>Size:</strong> {size_mb:.1f} MB</div>
"""

            # Add preset/parameters if available
            if 'preset' in variant:
                html_content += f"""                    <div><strong>Preset:</strong> {variant['preset']}</div>"""
            if 'params' in variant:
                params = variant['params']
                html_content += f"""                    <div><strong>Parameters:</strong> speed={params.get('length_scale', 'N/A')}, stability={params.get('noise_scale', 'N/A')}, clarity={params.get('noise_w', 'N/A')}</div>"""

            html_content += """
                </div>
            </div>
"""

        html_content += """
        </div>

        <div class="stats">
            <h3>Statistics</h3>
"""

        # Duration comparison table
        if analysis.get('duration_comparison'):
            html_content += """
            <h4>Duration Comparison</h4>
            <table>
                <tr><th>Variant</th><th>Duration (seconds)</th></tr>
"""
            for name, duration in sorted(analysis['duration_comparison'].items()):
                html_content += f"                <tr><td>{name}</td><td>{duration:.1f}</td></tr>\n"
            html_content += "            </table>"

        # Size comparison table
        if analysis.get('size_comparison'):
            html_content += """
            <h4>File Size Comparison</h4>
            <table>
                <tr><th>Variant</th><th>Size (MB)</th></tr>
"""
            for name, size_mb in sorted(analysis['size_comparison'].items()):
                html_content += f"                <tr><td>{name}</td><td>{size_mb:.1f}</td></tr>\n"
            html_content += "            </table>"

        html_content += """
        </div>
    </div>
</body>
</html>
"""

        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)

        return html_file

    def _export_csv_report(self, metadata: Dict, analysis: Dict, chapter_dir: Path) -> Path:
        """Export comparison data to CSV format."""
        chapter_name = metadata.get('chapter', 'unknown')
        csv_file = chapter_dir / f"{chapter_name}_comparison.csv"

        variants = [v for v in metadata.get('variants', []) if v.get('success', False)]

        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)

            # Write header
            writer.writerow(['Variant Name', 'Engine', 'Model', 'Preset', 'Duration (s)', 'Size (MB)',
                           'Length Scale', 'Noise Scale', 'Noise W', 'Generation Time (s)'])

            # Write data
            for variant in variants:
                params = variant.get('params', {})
                writer.writerow([
                    variant.get('name', ''),
                    variant.get('engine', ''),
                    variant.get('model', ''),
                    variant.get('preset', ''),
                    variant.get('duration_seconds', 0),
                    variant.get('file_size_bytes', 0) / (1024 * 1024),
                    params.get('length_scale', ''),
                    params.get('noise_scale', ''),
                    params.get('noise_w', ''),
                    variant.get('generation_time', 0)
                ])

        return csv_file

    def list_available_chapters(self) -> List[str]:
        """List chapters that have variant comparisons available."""
        chapters = []
        if self.variants_dir.exists():
            for item in self.variants_dir.iterdir():
                if item.is_dir() and (item / "variants_metadata.json").exists():
                    chapters.append(item.name)
        return sorted(chapters)


def main():
    """Main entry point for voice variant comparison script."""
    parser = argparse.ArgumentParser(
        description="Compare voice variants with audio players and analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/compare_voice_variants.py chapter_32b                    # Compare specific chapter
  python scripts/compare_voice_variants.py --list                        # List available chapters
  python scripts/compare_voice_variants.py chapter_32b --no-html         # CSV only
  python scripts/compare_voice_variants.py chapter_32b --open            # Open in browser
        """
    )

    parser.add_argument(
        'chapter',
        nargs='?',
        help='Chapter name to compare (use --list to see available chapters)'
    )

    parser.add_argument(
        '--list', '-l',
        action='store_true',
        help='List available chapters for comparison'
    )

    parser.add_argument(
        '--no-html',
        action='store_true',
        help='Skip HTML report generation (CSV only)'
    )

    parser.add_argument(
        '--open', '-o',
        action='store_true',
        help='Open HTML report in default browser'
    )

    parser.add_argument(
        '--variants-dir',
        default='data/5-audio-chunks/variants',
        help='Directory containing variant outputs'
    )

    args = parser.parse_args()

    try:
        comparer = VoiceVariantComparer(args.variants_dir)

        if args.list:
            # List available chapters
            chapters = comparer.list_available_chapters()
            if chapters:
                print("Available chapters for comparison:")
                for chapter in chapters:
                    print(f"  - {chapter}")
                print(f"\nTotal: {len(chapters)} chapters")
            else:
                print("No chapters available for comparison.")
                print("Generate some variants first using generate_voice_variants.py")

        elif args.chapter:
            # Compare specific chapter
            results = comparer.compare_chapter(
                args.chapter,
                output_html=not args.no_html,
                open_browser=args.open
            )

            if results:
                print(f"✓ Comparison completed for {args.chapter}")
                if not args.no_html:
                    print(f"HTML report: {results.get('html_report', 'N/A')}")
                print(f"CSV report: {results.get('csv_report', 'N/A')}")
            else:
                print(f"✗ No comparison data available for {args.chapter}")

        else:
            parser.print_help()

    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
    except Exception as e:
        logger.error(f"Error: {e}")
        exit(1)


if __name__ == "__main__":
    main()
