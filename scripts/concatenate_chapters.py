#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script to concatenate chapter parts and organize audio files
"""

import os
import re
import shutil
from collections import defaultdict
from pathlib import Path


def get_chapter_number(filename):
    """Extract chapter number from filename."""
    match = re.search(r"chapter_(\d+)", filename)
    return int(match.group(1)) if match else None


def get_chapter_part(filename):
    """Extract chapter part (a, b, c, etc) from filename."""
    match = re.search(r"chapter_\d+([a-z])", filename)
    return match.group(1) if match else None


def concatenate_markdown_files(input_dir, output_dir):
    """Concatenate markdown files and organize audio files."""
    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)

    # Group files by chapter number
    chapter_files = defaultdict(list)
    for file in input_dir.glob("*.md"):
        chapter_num = get_chapter_number(file.name)
        if chapter_num:
            chapter_files[chapter_num].append(file)

    # Sort files within each chapter by part
    for chapter_num in chapter_files:
        chapter_files[chapter_num].sort(key=lambda x: get_chapter_part(x.name) or "")

    # Process each chapter
    for chapter_num, files in sorted(chapter_files.items()):
        output_file = output_dir / f"chapter_{chapter_num}.md"
        print(f"Processing chapter {chapter_num}...")

        # Skip if output file already exists
        if output_file.exists():
            print(f"Chapter {chapter_num} already exists, skipping...")
            continue

        # Concatenate content
        content = []
        for file in files:
            with open(file, "r", encoding="utf-8") as f:
                file_content = f.read().strip()
                if file_content:
                    content.append(file_content)

        # Write concatenated content
        if content:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write("\n\n".join(content))
            print(f"Created {output_file}")


def main():
    # Define directories
    base_dir = Path("/home/sparrow/projects/human-action")
    markdown_dir = base_dir / "data/4-markdown-chunks-optimized"
    output_dir = base_dir / "data/6-audio-chapters-espeak"

    # Process files
    concatenate_markdown_files(markdown_dir, output_dir)
    print("Done!")


if __name__ == "__main__":
    main()
