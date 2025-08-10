#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
PDF Processor for Lidské Jednání Project
---------------------------------------

Extracts text from PDF files and creates markdown chapter files.
Input: PDF file from data/1-pdf
Output: Markdown chapter files in data/2-markdown-chapters
"""

import argparse
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import re

import pypdf

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("pdf_processing.log")],
)
logger = logging.getLogger(__name__)


class PDFProcessor:
    """Extracts text from PDF files and creates markdown chapter files."""

    input_dir: Path
    output_dir: Path
    pdf_files: List[Path]
    chapters: List[Dict[str, Any]]

    def __init__(
        self,
        input_dir: str = "/home/sparrow/projects/LidskeJednani/data/1-pdf",
        output_dir: str = "/home/sparrow/projects/LidskeJednani/data/2-markdown-chapters",
    ):
        """
        Initialize the PDF Processor.

        Args:
            input_dir: Directory containing PDF files
            output_dir: Directory for output markdown chapters
        """
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)

        # Create output directory if it doesn't exist
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize state
        self.pdf_files = []
        self.chapters = []

    def scan_input_directory(self) -> List[Path]:
        """
        Scan the input directory for PDF files.

        Returns:
            List of PDF file paths
        """
        self.pdf_files = list(self.input_dir.glob("*.pdf"))
        logger.info(f"Found {len(self.pdf_files)} PDF files in {self.input_dir}")
        return self.pdf_files

    def extract_text_from_pdf(self, pdf_path: Path) -> str:
        """
        Extract text from a PDF file.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Extracted text
        """
        # TODO: Implement PDF text extraction
        logger.info(f"Extracting text from {pdf_path}")
        try:
            reader = pypdf.PdfReader(str(pdf_path))
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            return text
        except Exception as e:
            logger.error(f"Error extracting text from {pdf_path.name}: {e}")
            return f"Error extracting text from {pdf_path.name}"

    def detect_chapters(self, text: str) -> List[Dict[str, Any]]:
        """
        Detect chapters in the extracted text.

        Args:
            text: Extracted text from PDF

        Returns:
            List of chapters with their content
        """
        # TODO: Implement chapter detection more robustly (handle Parts, Roman numerals, etc.)
        logger.info("Detecting chapters in the text...")
        self.chapters = []
        lines = text.split('\n')
        current_chapter_content = []
        current_chapter_number = 0 # Start with chapter 0 for preface/intro
        current_chapter_title = "Předmluva" # Default title for content before Chapter 1

        # Regex to find lines like "Kapitola 1. Title" or "Kapitola 5"
        chapter_pattern = re.compile(r"^\s*Kapitola\s+(\d+)\.?\s*(.*)$", re.IGNORECASE)

        for line in lines:
            match = chapter_pattern.match(line)
            if match:
                # Found a new chapter marker
                # Save the previous chapter's content if it exists
                if current_chapter_content:
                    self.chapters.append({
                        "number": current_chapter_number,
                        "title": current_chapter_title.strip(),
                        "content": '\n'.join(current_chapter_content).strip()
                    })

                # Start the new chapter
                current_chapter_number = int(match.group(1))
                current_chapter_title = match.group(2).strip() if match.group(2) else f"Kapitola {current_chapter_number}"
                current_chapter_content = [line] # Include the chapter title line itself
                logger.info(f"Detected Chapter {current_chapter_number}: {current_chapter_title}")

            else:
                # Add line to the current chapter's content
                current_chapter_content.append(line)

        # Save the last chapter's content
        if current_chapter_content:
            self.chapters.append({
                "number": current_chapter_number,
                "title": current_chapter_title.strip(),
                "content": '\n'.join(current_chapter_content).strip()
            })

        if not self.chapters:
             logger.warning("No chapters were detected. Saving entire text as Chapter 0.")
             self.chapters.append({
                 "number": 0,
                 "title": "Full Text",
                 "content": text
             })

        logger.info(f"Detected {len(self.chapters)} chapters in total.")
        return self.chapters

    def save_chapters(self) -> List[Path]:
        """
        Save chapters to markdown files.

        Returns:
            List of saved chapter file paths
        """
        saved_files = []

        def sanitize_filename(name: str) -> str:
            """Remove or replace characters unsuitable for filenames."""
            # Remove punctuation and symbols, replace spaces with underscores
            name = re.sub(r'[\\/:*?"<>|]', '', name) # Remove illegal characters
            name = re.sub(r'\s+', '_', name) # Replace spaces with underscores
            return name[:100] # Limit length to avoid issues

        for chapter in self.chapters:
            try:
                chapter_num = chapter['number']
                chapter_title = chapter.get('title', f'Kapitola_{chapter_num}')
                chapter_content = chapter.get('content', '')

                sanitized_title = sanitize_filename(chapter_title)
                filename = f"chapter_{chapter_num:02d}_{sanitized_title}.md"
                file_path = self.output_dir / filename

                # Write content to file
                with open(file_path, "w", encoding="utf-8") as f:
                    # Write title as H1 header if not already present in content
                    if not chapter_content.strip().startswith(f"# {chapter_title}"):
                         f.write(f"# {chapter_title}\n\n")
                    f.write(chapter_content)

                saved_files.append(file_path)
                logger.info(f"Saved chapter {chapter_num} to {file_path}")

            except IOError as e:
                logger.error(f"Error writing chapter {chapter.get('number', '?')} to file: {e}")
            except Exception as e:
                 logger.error(f"Unexpected error saving chapter {chapter.get('number', '?')}: {e}")

        return saved_files

    def process(self, pdf_path: Optional[Path] = None) -> List[Path]:
        """
        Process a PDF file and extract chapters.

        Args:
            pdf_path: Path to the PDF file (if None, processes the first found PDF)

        Returns:
            List of paths to the generated markdown files
        """
        # If no PDF path provided, scan directory and use the first found
        if pdf_path is None:
            self.scan_input_directory()
            if not self.pdf_files:
                logger.error(f"No PDF files found in {self.input_dir}")
                return []
            pdf_path = self.pdf_files[0]

        # Extract text from PDF
        text = self.extract_text_from_pdf(pdf_path)

        # Detect chapters
        self.detect_chapters(text)

        # Save chapters to files
        return self.save_chapters()


def main():
    """Main function to run the PDF processor from command line."""
    parser = argparse.ArgumentParser(
        description="Extract text from PDF and create markdown chapter files"
    )

    parser.add_argument(
        "-i",
        "--input-dir",
        type=str,
        default="/home/sparrow/projects/LidskeJednani/data/1-pdf",
        help="Directory containing PDF files",
    )

    parser.add_argument(
        "-o",
        "--output-dir",
        type=str,
        default="/home/sparrow/projects/LidskeJednani/data/2-markdown-chapters",
        help="Directory for output markdown chapters",
    )

    parser.add_argument(
        "-f", "--file", type=str, help="Specific PDF file to process (optional)"
    )

    args = parser.parse_args()

    try:
        processor = PDFProcessor(args.input_dir, args.output_dir)

        if args.file:
            pdf_path = Path(args.file)
            if not pdf_path.exists():
                logger.error(f"File not found: {pdf_path}")
                return
            processor.process(pdf_path)
        else:
            processor.process()

    except Exception as e:
        logger.error(f"Error processing PDF: {str(e)}")


if __name__ == "__main__":
    main()
