import os
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

from scripts.separate_paragraphs import ParagraphSeparator


class TestParagraphSeparator:

    def test_separate_paragraphs(self, test_config):
        """Test separating paragraphs in markdown content"""
        # Create a test file with paragraphs
        input_dir = test_config.markdown_chapters_dir
        output_dir = test_config.paragraphs_dir
        output_dir.mkdir(exist_ok=True)

        test_file = input_dir / "test_chapter.md"
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("# Test Chapter\n\n")
            f.write("This is the first paragraph. It has multiple sentences.\n")
            f.write("This is still the first paragraph.\n\n")
            f.write("This is the second paragraph.\n\n")
            f.write("## Section Heading\n\n")
            f.write("This is the third paragraph after a heading.\n")

        # Create the paragraph separator
        separator = ParagraphSeparator(input_dir=input_dir, output_dir=output_dir)

        # Call the method to test
        output_files = separator.process(test_file)

        # Check results
        assert len(output_files) > 0, "No output files generated"

        # Read all output files
        paragraph_texts = []
        for output_file in sorted(output_files):
            with open(output_file, "r", encoding="utf-8") as f:
                paragraph_texts.append(f.read().strip())

        # Check paragraphs were correctly separated
        assert "# Test Chapter" in paragraph_texts[0], "Chapter title not preserved"
        assert (
            "This is the first paragraph" in paragraph_texts[1]
        ), "First paragraph not preserved"
        assert (
            "This is the second paragraph" in paragraph_texts[2]
        ), "Second paragraph not preserved"
        assert (
            "## Section Heading" in paragraph_texts[3]
        ), "Section heading not preserved"
        assert (
            "This is the third paragraph" in paragraph_texts[4]
        ), "Third paragraph not preserved"

    def test_process_directory(self, test_config):
        """Test processing all markdown files in a directory"""
        # Create test files
        input_dir = test_config.markdown_chapters_dir
        output_dir = test_config.paragraphs_dir
        output_dir.mkdir(exist_ok=True)

        # Create two test chapters
        for i in range(2):
            chapter_file = input_dir / f"chapter_{i+1:02d}.md"
            with open(chapter_file, "w", encoding="utf-8") as f:
                f.write(f"# Chapter {i+1}\n\n")
                # Create 3 paragraphs per chapter
                for j in range(3):
                    f.write(f"This is paragraph {j+1} in chapter {i+1}.\n\n")

        # Create the paragraph separator
        separator = ParagraphSeparator(input_dir=input_dir, output_dir=output_dir)

        # Call the method to test
        all_output_files = separator.process()

        # Check results
        assert len(all_output_files) > 0, "No output files generated"

        # We should get at least 8 files: 2 titles + 6 paragraphs
        assert (
            len(all_output_files) >= 8
        ), f"Expected at least 8 output files, got {len(all_output_files)}"

        # Check output directory contains the expected files
        output_files = list(Path(output_dir).glob("*.md"))

        # Check that files exist and follow the correct naming pattern
        file_stems = [file.stem for file in output_files]

        # Check if files for both chapters exist
        for i in range(2):
            chapter_prefix = f"chapter_{i+1:02d}"
            chapter_files = [
                stem for stem in file_stems if stem.startswith(chapter_prefix)
            ]
            assert len(chapter_files) > 0, f"No files found for {chapter_prefix}"
