import os
import pytest
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

# First, let's create a simple espeak audio generator for testing
# We'll save this in a separate file later, but include it here for the test
# The actual implementation will go in espeak_audio_chunk_generator.py
class EspeakAudioChunkGenerator:
    """Audio generator that uses espeak instead of ElevenLabs for testing"""
    
    def __init__(self, input_dir, output_dir, language="cs"):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.language = language
        
        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)
    
    def synthesize_chunk(self, input_file):
        """Synthesize a single chunk using espeak"""
        # Get the stem name from the input file (without extension)
        base_name = Path(input_file).stem
        output_file = self.output_dir / f"{base_name}.mp3" 
        
        # Read the markdown content
        with open(input_file, 'r', encoding='utf-8') as f:
            text = f.read()
        
        # Use espeak to generate audio
        cmd = [
            'espeak',
            f'--voice={self.language}',
            '--stdout',
            text
        ]
        
        # Redirect espeak output to a file
        with open(output_file, 'wb') as f:
            subprocess.run(cmd, stdout=f, check=True)
        
        return output_file
    
    def process(self, directory=None):
        """Process all markdown files in the input directory"""
        directory = directory or self.input_dir
        input_files = sorted(list(Path(directory).glob('*.md')))
        
        output_files = []
        for input_file in input_files:
            output_file = self.synthesize_chunk(input_file)
            output_files.append(output_file)
            
        return output_files


class TestEspeakAudioGenerator:
    
    @patch('subprocess.run')
    def test_synthesize_chunk(self, mock_subprocess_run, test_config, setup_test_files):
        """Test synthesizing a single chunk with mocked subprocess"""
        # Configure the mock
        mock_subprocess_run.return_value = MagicMock(returncode=0)
        
        # Create test input file
        input_dir = test_config.markdown_chunks_dir
        output_dir = test_config.audio_chunks_dir
        
        # Create a test chunk
        test_chunk_path = input_dir / "test_chunk.md"
        with open(test_chunk_path, 'w', encoding='utf-8') as f:
            f.write("This is a test chunk for audio synthesis.")
        
        # Create the generator
        generator = EspeakAudioChunkGenerator(
            input_dir=input_dir,
            output_dir=output_dir
        )
        
        # Call the method to test
        output_file = generator.synthesize_chunk(test_chunk_path)
        
        # Check results
        assert output_file.parent == output_dir, "Output file in wrong directory"
        assert output_file.stem == "test_chunk", "Output filename doesn't match input stem"
        assert output_file.suffix == ".mp3", "Output file has wrong extension"
        
        # Verify the subprocess call
        mock_subprocess_run.assert_called_once()
        args, kwargs = mock_subprocess_run.call_args
        
        # Check command arguments
        cmd = args[0]
        assert 'espeak' in cmd[0], "espeak command not called"
        assert '--voice=cs' in cmd, "Voice not set correctly"
        assert '--stdout' in cmd, "stdout redirection not set"
        
        # Check that the call was made with the check=True parameter
        assert kwargs.get('check') is True, "subprocess.run not called with check=True"
    
    @patch('subprocess.run')
    def test_process_all_chunks(self, mock_subprocess_run, test_config, setup_test_files):
        """Test processing all chunks in a directory"""
        # Configure the mock
        mock_subprocess_run.return_value = MagicMock(returncode=0)
        
        # Create test input files
        input_dir = test_config.markdown_chunks_dir
        output_dir = test_config.audio_chunks_dir
        
        # Create three test chunks
        for i in range(3):
            chunk_path = input_dir / f"chunk_{i}.md"
            with open(chunk_path, 'w', encoding='utf-8') as f:
                f.write(f"This is test chunk {i} for audio synthesis.")
        
        # Create the generator
        generator = EspeakAudioChunkGenerator(
            input_dir=input_dir,
            output_dir=output_dir
        )
        
        # Call the method to test
        output_files = generator.process()
        
        # Check results
        assert len(output_files) == 3, "Expected 3 output files"
        for i, output_file in enumerate(sorted(output_files)):
            assert output_file.parent == output_dir, f"Output file {i} in wrong directory"
            assert output_file.stem == f"chunk_{i}", f"Output filename {i} doesn't match input stem"
            assert output_file.suffix == ".mp3", f"Output file {i} has wrong extension"
        
        # Verify the subprocess calls
        assert mock_subprocess_run.call_count == 3, "subprocess.run not called 3 times" 