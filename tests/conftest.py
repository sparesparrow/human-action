import os
import sys
import pytest
import tempfile
import shutil
from pathlib import Path

# Add project root to Python path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files"""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    # Clean up after tests
    shutil.rmtree(temp_dir)

@pytest.fixture
def test_config(temp_dir):
    """Create a test configuration with temporary directories"""
    # Create a class with the same attributes expected by tests
    class TestConfig:
        def __init__(self, base_dir):
            self.base_dir = Path(base_dir)
            self.pdf_dir = self.base_dir / "pdf"
            self.markdown_chapters_dir = self.base_dir / "markdown_chapters"
            self.markdown_chunks_dir = self.base_dir / "markdown_chunks"
            self.markdown_paragraphs_dir = self.base_dir / "paragraphs"
            self.audio_chunks_dir = self.base_dir / "audio_chunks"
            self.audio_book_dir = self.base_dir / "audio_book"
            
            # Create all directories
            for directory in [
                self.pdf_dir,
                self.markdown_chapters_dir,
                self.markdown_chunks_dir,
                self.markdown_paragraphs_dir,
                self.audio_chunks_dir,
                self.audio_book_dir
            ]:
                directory.mkdir(parents=True, exist_ok=True)
    
    # Initialize the test configuration
    config = TestConfig(temp_dir)
    return config

@pytest.fixture
def sample_markdown_path():
    """Path to sample markdown file"""
    return Path(__file__).parent / "fixtures" / "sample.md"

@pytest.fixture
def setup_test_files(test_config, sample_markdown_path):
    """Copy sample files to test directories"""
    # Copy sample markdown to chapters dir
    chapter_file = test_config.markdown_chapters_dir / "chapter_01.md"
    shutil.copy(sample_markdown_path, chapter_file)
    
    return {
        "chapter_file": chapter_file
    } 