import os
from pathlib import Path

import pytest

from chunker_splitter import MarkdownChunker


class TestChunkerSplitter:

    def test_split_into_chunks(self, test_config, setup_test_files):
        """Test that markdown file is properly split into chunks"""
        # Get the input file
        input_file = setup_test_files["chapter_file"]

        # Create the chunker
        chunker = MarkdownChunker(
            input_dir=str(test_config.markdown_chapters_dir),
            output_dir=str(test_config.markdown_chunks_dir),
            max_chunk_size=1000,
        )

        # Run the chunker
        output_files = chunker.process_file(input_file)

        # Check results
        assert len(output_files) > 0, "No output files were generated"

        # Check that files were created
        for file_path in output_files:
            assert Path(file_path).exists(), f"Output file {file_path} does not exist"

            # Check content of each file
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                # Each chunk should be less than max_chunk_size (with some margin for ending paragraphs)
                assert (
                    len(content) <= 1200
                ), f"Chunk size exceeds max_chars significantly: {len(content)}"
                # Each chunk should contain valid content
                assert len(content.strip()) > 0, "Chunk is empty"

        # Check naming pattern
        for i, file_path in enumerate(sorted(output_files)):
            expected_suffix = chr(97 + i)  # a, b, c, ...
            assert f"chapter_01{expected_suffix}" in str(
                file_path
            ), f"Wrong file naming pattern for chunk {i}"

    def test_split_with_too_small_max_chars(self, test_config, setup_test_files):
        """Test with very small max_chunk_size value"""
        # Get the input file
        input_file = setup_test_files["chapter_file"]

        # Create the chunker with very small max_chunk_size
        chunker = MarkdownChunker(
            input_dir=str(test_config.markdown_chapters_dir),
            output_dir=str(test_config.markdown_chunks_dir),
            max_chunk_size=50,  # Deliberately small to test handling of min chunk size
        )

        # Run the chunker
        output_files = chunker.process_file(input_file)

        # Check if any files were generated
        assert (
            len(output_files) > 0
        ), "No output files were generated with small max_chars"

        # Each chunk should contain at least one sentence or paragraph
        for file_path in output_files:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                assert len(content.strip()) > 0, "Chunk is empty"
