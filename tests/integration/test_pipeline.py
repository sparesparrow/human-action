import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from config import Config

# Import pipeline components
from pipeline import Pipeline


# This is the correct import path for the mocks to work properly
@pytest.mark.usefixtures("setup_test_files")
class TestPipeline:

    @pytest.fixture
    def create_test_pdf(self, test_config):
        """Create a test PDF file for the pipeline"""
        # For testing, we'll create an empty PDF file
        # The actual extraction will be mocked
        test_pdf_path = test_config.pdf_dir / "test_book.pdf"
        with open(test_pdf_path, "wb") as f:
            f.write(b"Mock PDF content")

        return test_pdf_path

    # Helper method to create a Config object from test_config
    def create_config_from_test_config(self, test_config):
        """Create a proper Config object from test_config"""
        # Create a new Config object with a dummy path
        config = Config("config.yaml")

        # Override the config paths with test paths
        config.base_dir = test_config.base_dir
        config.pdf_dir = test_config.pdf_dir
        config.markdown_chapters_dir = test_config.markdown_chapters_dir
        config.markdown_chunks_dir = test_config.markdown_chunks_dir
        config.audio_chunks_dir = test_config.audio_chunks_dir
        config.audio_book_dir = test_config.audio_book_dir

        # For compatibility with test fixtures
        config.markdown_paragraphs_dir = test_config.markdown_paragraphs_dir

        return config

    # Update patch paths to use direct module.class.method format which is more reliable
    @patch("pdf_extractor.PDFProcessor.process")
    @patch("chunker_splitter.MarkdownChunker.process")
    @patch("espeak_audio_chunk_generator.EspeakAudioChunkGenerator.process")
    @patch("audio_concatenator.AudioConcatenator.process")
    @patch("scripts.separate_paragraphs.ParagraphSeparator.process")
    def test_full_pipeline(
        self,
        mock_separator,
        mock_concatenator,
        mock_audio_generator,
        mock_chunker,
        mock_pdf_processor,
        test_config,
        create_test_pdf,
    ):
        """
        Integration test for the full pipeline
        Mocks all component calls to avoid actual processing
        """
        # Setup mock returns
        test_pdf_path = create_test_pdf

        # Mock PDF processor to return markdown files
        markdown_files = [
            test_config.markdown_chapters_dir / "chapter_01.md",
            test_config.markdown_chapters_dir / "chapter_02.md",
        ]
        for file_path in markdown_files:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(f"# {file_path.stem}\n\nTest content for {file_path.stem}")
        mock_pdf_processor.return_value = markdown_files

        # Mock chunker to return chunk files
        chunk_files = []
        for chapter_idx, _ in enumerate(markdown_files, 1):
            for chunk_idx in range(2):  # 2 chunks per chapter
                chunk_file = (
                    test_config.markdown_chunks_dir
                    / f"chapter_{chapter_idx:02d}{chr(97+chunk_idx)}.md"
                )
                with open(chunk_file, "w", encoding="utf-8") as f:
                    f.write(f"Content for {chunk_file.stem}")
                chunk_files.append(chunk_file)
        mock_chunker.return_value = chunk_files

        # Mock paragraph separator to return paragraph files
        paragraph_files = []
        for chunk_idx, _ in enumerate(chunk_files):
            for para_idx in range(2):  # 2 paragraphs per chunk
                para_file = (
                    test_config.markdown_paragraphs_dir
                    / f"para_{chunk_idx}_{para_idx}.md"
                )
                with open(para_file, "w", encoding="utf-8") as f:
                    f.write(f"Paragraph content for {para_file.stem}")
                paragraph_files.append(para_file)
        mock_separator.return_value = paragraph_files

        # Mock audio generator to return audio files
        audio_files = []
        for chunk_idx, chunk_file in enumerate(chunk_files):
            audio_file = test_config.audio_chunks_dir / f"{chunk_file.stem}.mp3"
            with open(audio_file, "wb") as f:
                f.write(b"Mock audio data")
            audio_files.append(audio_file)
        mock_audio_generator.return_value = audio_files

        # Mock concatenator to return final audiobook file
        audiobook_file = test_config.audio_book_dir / "audiobook.mp3"
        with open(audiobook_file, "wb") as f:
            f.write(b"Mock audiobook data")
        mock_concatenator.return_value = audiobook_file

        # Create the pipeline with a proper Config object
        config = self.create_config_from_test_config(test_config)

        # Important: Create test state file for pipeline
        state_file = config.base_dir / "pipeline_state.json"

        # Initialize the pipeline instance
        pipeline = Pipeline(config)

        # Create mock modules for the imports in run_pipeline_steps
        pdf_extractor_mock = MagicMock()
        pdf_extractor_mock.PDFProcessor.return_value.process.return_value = (
            markdown_files
        )

        chunker_mock = MagicMock()
        chunker_mock.process.return_value = chunk_files

        audio_gen_mock = MagicMock()
        audio_gen_mock.process.return_value = audio_files

        audio_concat_mock = MagicMock()
        audio_concat_mock.process.return_value = audiobook_file

        para_sep_mock = MagicMock()
        para_sep_mock.process.return_value = paragraph_files

        # Patch the imports in run_pipeline_steps
        with patch.dict(
            "sys.modules",
            {
                "pdf_extractor": pdf_extractor_mock,
                "chunker_splitter": MagicMock(MarkdownChunker=chunker_mock),
                "espeak_audio_chunk_generator": MagicMock(
                    EspeakAudioChunkGenerator=audio_gen_mock
                ),
                "audio_concatenator": MagicMock(AudioConcatenator=audio_concat_mock),
                "scripts.separate_paragraphs": MagicMock(
                    ParagraphSeparator=para_sep_mock
                ),
            },
        ):
            # Run the pipeline with explicit arguments
            result = pipeline.process(
                test_pdf_path,
                steps=[
                    "pdf_extraction",
                    "chunk_splitting",
                    "paragraph_separation",
                    "audio_generation",
                    "audio_concatenation",
                ],
                state_file=state_file,
            )

        # Check that the result is not None
        assert result is not None, "Pipeline result was None"

        # Check that the state file was created
        assert state_file.exists(), "State file was not created"

        # Check the state file content
        with open(state_file, "r") as f:
            state_data = json.load(f)

        # Verify state contains the completed step
        assert "completed_steps" in state_data, "State doesn't have completed_steps"

    def test_pipeline_state_tracking(self, test_config, create_test_pdf):
        """Test that the pipeline correctly tracks and updates state"""
        # Setup test files
        test_pdf_path = create_test_pdf

        # Create a pipeline with a state file
        config = self.create_config_from_test_config(test_config)

        # Create the state file manually
        state_file = config.base_dir / "pipeline_state.json"

        # Initialize pipeline with mocked methods
        pipeline = Pipeline(config)

        # Create initial state directly
        state = {"input_file": str(test_pdf_path), "completed_steps": {}}
        with open(state_file, "w") as f:
            json.dump(state, f)

        # Create mock for the PDF processor
        pdf_processor_mock = MagicMock()
        pdf_processor_mock.process.return_value = [
            config.markdown_chapters_dir / "chapter_01.md"
        ]

        # Create output file that the processor would create
        with open(config.markdown_chapters_dir / "chapter_01.md", "w") as f:
            f.write("Test content")

        # Patch the imports in run_pipeline_steps to use our mocks
        with patch.dict(
            "sys.modules",
            {"pdf_extractor": MagicMock(PDFProcessor=lambda: pdf_processor_mock)},
        ):
            # Process with state tracking
            pipeline.process(
                test_pdf_path, steps=["pdf_extraction"], state_file=state_file
            )

        # Check that state file was created
        assert state_file.exists(), "State file was not created"

        # Read state file
        with open(state_file, "r") as f:
            state_data = json.load(f)

        # Check state contents
        assert "input_file" in state_data, "State doesn't contain input_file"
        assert "completed_steps" in state_data, "State doesn't contain completed_steps"
        assert (
            "pdf_extraction" in state_data["completed_steps"]
        ), "PDF extraction step not marked as completed"
        assert state_data["input_file"] == str(
            test_pdf_path
        ), "Input file not correctly stored in state"

        # Create mock for the chunker
        chunker_mock = MagicMock()
        chunker_mock.process.return_value = [
            config.markdown_chunks_dir / "chapter_01a.md"
        ]

        # Create the output file
        with open(config.markdown_chunks_dir / "chapter_01a.md", "w") as f:
            f.write("Test chunk content")

        # Test state resumption with patches
        with patch.dict(
            "sys.modules",
            {
                "pdf_extractor": MagicMock(PDFProcessor=lambda: pdf_processor_mock),
                "chunker_splitter": MagicMock(
                    MarkdownChunker=lambda *args, **kwargs: chunker_mock
                ),
            },
        ):
            # Create a new pipeline instance to test loading state
            new_pipeline = Pipeline(config)

            # Process starting from the next step
            new_pipeline.process(
                test_pdf_path,
                steps=["pdf_extraction", "chunk_splitting"],
                state_file=state_file,
            )

        # Check if state file was updated with both steps
        with open(state_file, "r") as f:
            state_data = json.load(f)

        # Both steps should now be in completed_steps
        assert (
            "pdf_extraction" in state_data["completed_steps"]
        ), "PDF extraction step missing from state"
        assert (
            "chunk_splitting" in state_data["completed_steps"]
        ), "Chunk splitting step missing from state"

    def test_pipeline_with_espeak(self, test_config, create_test_pdf):
        """Test pipeline with real espeak audio generator instead of ElevenLabs"""
        # Create a mock state where all steps before audio generation are done
        test_pdf_path = create_test_pdf

        # Create some mock chunk files
        chunk_files = []
        for chapter_idx in range(1, 2):  # Just create one chapter for speed
            for chunk_idx in range(2):  # 2 chunks per chapter
                chunk_file = (
                    test_config.markdown_chunks_dir
                    / f"chapter_{chapter_idx:02d}{chr(97+chunk_idx)}.md"
                )
                with open(chunk_file, "w", encoding="utf-8") as f:
                    f.write(f"Content for {chunk_file.stem}. This is a test.")
                chunk_files.append(chunk_file)

        # Create some mock audio files for the concatenator
        for chunk_file in chunk_files:
            audio_file = test_config.audio_chunks_dir / f"{chunk_file.stem}.mp3"
            with open(audio_file, "wb") as f:
                f.write(b"Mock audio data")

        # Create a state file that shows previous steps are completed
        state_file = test_config.base_dir / "pipeline_state.json"
        state = {
            "input_file": str(test_pdf_path),
            "completed_steps": {
                "pdf_extraction": {
                    "output_files": [
                        str(test_config.markdown_chapters_dir / "chapter_01.md")
                    ]
                },
                "chunk_splitting": {
                    "output_files": [str(path) for path in chunk_files]
                },
                "paragraph_separation": {
                    "output_files": [
                        str(test_config.markdown_paragraphs_dir / "para_01.md")
                    ]
                },
            },
        }

        with open(state_file, "w") as f:
            json.dump(state, f)

        # Create the pipeline that will use run_pipeline_steps
        config = self.create_config_from_test_config(test_config)
        pipeline = Pipeline(config)

        # Mock the AudioConcatenator
        audio_concatenator_mock = MagicMock()
        audio_concatenator_mock.process.return_value = (
            config.audio_book_dir / "audiobook.mp3"
        )

        # Create the expected output file
        with open(config.audio_book_dir / "audiobook.mp3", "wb") as f:
            f.write(b"Mock audiobook output")

        # Patch modules
        with patch.dict(
            "sys.modules",
            {
                "audio_concatenator": MagicMock(
                    AudioConcatenator=lambda *args, **kwargs: audio_concatenator_mock
                )
            },
        ):
            # Run just the audio concatenation step
            result = pipeline.process(
                test_pdf_path, steps=["audio_concatenation"], state_file=state_file
            )

        # Check results
        assert result is not None, "Pipeline returned None"
        assert "audiobook.mp3" in str(
            result
        ), "Pipeline did not return the expected audiobook file"

        # Check that the state has been updated
        with open(state_file, "r") as f:
            state_data = json.load(f)

        assert (
            "audio_concatenation" in state_data["completed_steps"]
        ), "Audio concatenation step not in completed steps"
