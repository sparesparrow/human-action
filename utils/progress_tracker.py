#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Progress Tracker for Lidské Jednání Project
-------------------------------------------

Utility to track and report progress of the processing pipeline.
Generates statistics about the number of files in each stage of the pipeline.
"""

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import MaxNLocator

# Add parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Define project directories
PROJECT_ROOT = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = PROJECT_ROOT / "data"
PDF_DIR = DATA_DIR / "1-pdf"
MARKDOWN_DIR = DATA_DIR / "2-markdown-chapters"
CHUNKS_DIR = DATA_DIR / "3-markdown-chunks"
OPTIMIZED_DIR = DATA_DIR / "4-markdown-chunks-optimized"
AUDIO_CHUNKS_DIR = DATA_DIR / "5-audio-chunks"
AUDIO_CHAPTERS_DIR = DATA_DIR / "6-audio-chapters"

# Progress tracking file
PROGRESS_FILE = PROJECT_ROOT / "progress_log.csv"


def get_file_count(directory, pattern="*", processed_only=False):
    """Count files in a directory matching a pattern."""
    if not directory.exists():
        return 0

    if processed_only:
        # Count only files with AUDIO_GENERATED prefix
        return len(list(directory.glob(f"AUDIO_GENERATED-{pattern}")))
    else:
        return len(list(directory.glob(pattern)))


def get_pipeline_stats():
    """Get statistics for each stage of the pipeline."""
    stats = {
        "Stage": [
            "PDF Files",
            "Markdown Chapters",
            "Markdown Chunks",
            "Optimized Chunks",
            "Processed Chunks",
            "Audio Chunks",
            "Audio Chapters",
        ],
        "Count": [
            get_file_count(PDF_DIR, "*.pdf"),
            get_file_count(MARKDOWN_DIR, "*.md"),
            get_file_count(CHUNKS_DIR, "*.md")
            - get_file_count(CHUNKS_DIR, "*.md", processed_only=True),
            get_file_count(OPTIMIZED_DIR, "*.md")
            - get_file_count(OPTIMIZED_DIR, "*.md", processed_only=True),
            get_file_count(OPTIMIZED_DIR, "*.md", processed_only=True)
            + get_file_count(CHUNKS_DIR, "*.md", processed_only=True),
            get_file_count(AUDIO_CHUNKS_DIR, "*.mp3"),
            get_file_count(AUDIO_CHAPTERS_DIR, "*.mp3"),
        ],
    }
    return pd.DataFrame(stats)


def log_progress():
    """Log the current progress to a CSV file."""
    stats = get_pipeline_stats()
    stats["Date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Check if the log file exists
    if not PROGRESS_FILE.exists():
        stats.to_csv(PROGRESS_FILE, index=False)
    else:
        # Read existing data and append new stats
        existing_data = pd.read_csv(PROGRESS_FILE)
        updated_data = pd.concat([existing_data, stats], ignore_index=True)
        updated_data.to_csv(PROGRESS_FILE, index=False)

    print(f"Progress logged to {PROGRESS_FILE}")


def display_progress():
    """Display current progress of the pipeline."""
    stats = get_pipeline_stats()

    # Print table
    print("\nCurrent Pipeline Status:")
    print("=" * 40)
    for _, row in stats.iterrows():
        print(f"{row['Stage']:<20}: {row['Count']:>5}")
    print("=" * 40)

    # Calculate overall progress
    if stats["Count"][0] > 0:  # If there are PDF files
        total_chapters = stats["Count"][1]
        total_expected_chunks = total_chapters * 3  # Approximate
        current_chunks = stats["Count"][2] + stats["Count"][3] + stats["Count"][4]
        chunk_progress = min(
            100,
            (
                current_chunks / total_expected_chunks * 100
                if total_expected_chunks > 0
                else 0
            ),
        )

        audio_progress = (
            stats["Count"][5] / current_chunks * 100 if current_chunks > 0 else 0
        )
        chapter_progress = (
            stats["Count"][6] / total_chapters * 100 if total_chapters > 0 else 0
        )

        print(f"Chunk Processing: {chunk_progress:.1f}% complete")
        print(f"Audio Generation: {audio_progress:.1f}% complete")
        print(f"Chapter Assembly: {chapter_progress:.1f}% complete")

        # Overall progress weighted
        overall = chunk_progress * 0.3 + audio_progress * 0.5 + chapter_progress * 0.2
        print(f"Overall Progress: {overall:.1f}%\n")


def plot_progress():
    """Plot progress over time from the log file."""
    if not PROGRESS_FILE.exists():
        print("No progress log found. Run with --log first.")
        return

    # Read progress data
    data = pd.read_csv(PROGRESS_FILE)

    # Convert date to datetime
    data["Date"] = pd.to_datetime(data["Date"])

    # Create a pivot table for plotting
    pivot_data = pd.pivot_table(data, values="Count", index="Date", columns="Stage")

    # Plot
    plt.figure(figsize=(12, 8))

    # Plot file counts by stage
    ax = pivot_data.plot(kind="line", marker="o")
    ax.set_title("Processing Pipeline Progress")
    ax.set_xlabel("Date")
    ax.set_ylabel("File Count")
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    ax.grid(True)

    # Save the plot
    plot_path = PROJECT_ROOT / "progress_plot.png"
    plt.tight_layout()
    plt.savefig(plot_path)
    print(f"Progress plot saved to {plot_path}")

    # Show the plot if running in an interactive environment
    plt.show()


def main():
    """Main function with command-line argument parsing."""
    parser = argparse.ArgumentParser(
        description="Track and visualize progress of the Lidské Jednání processing pipeline"
    )

    parser.add_argument(
        "--log", action="store_true", help="Log current progress to CSV file"
    )

    parser.add_argument(
        "--plot", action="store_true", help="Generate a plot of progress over time"
    )

    args = parser.parse_args()

    # Always display current progress
    display_progress()

    # Log progress if requested
    if args.log:
        log_progress()

    # Plot progress if requested
    if args.plot:
        plot_progress()


if __name__ == "__main__":
    main()
