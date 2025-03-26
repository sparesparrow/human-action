import os
import pytest
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock, call

# Import the module to test
import audio_concatenator

class TestAudioConcatenator:
    
    @patch('subprocess.run')
    def test_concatenate_audio_files(self, mock_subprocess_run, test_config):
        """Test concatenating audio files with mocked subprocess"""
        # Configure the mock
        mock_subprocess_run.return_value = MagicMock(returncode=0)
        
        # Create input files (just empty files for testing)
        input_dir = test_config.audio_chunks_dir
        os.makedirs(input_dir, exist_ok=True)
        
        audio_files = []
        for i in range(3):
            file_path = input_dir / f"chunk_{i}.mp3"
            with open(file_path, 'wb') as f:
                f.write(b"mock audio data")
            audio_files.append(file_path)
        
        # Set up output file
        output_dir = test_config.audio_book_dir
        os.makedirs(output_dir, exist_ok=True)
        output_file = output_dir / "output.mp3"
        
        # Create the concatenator
        concatenator = audio_concatenator.AudioConcatenator(
            input_dir=input_dir,
            output_dir=output_dir
        )
        
        # Call the method to test
        result_file = concatenator.concatenate_audio_files(
            audio_files=audio_files,
            output_file=output_file
        )
        
        # Check results
        assert result_file == output_file, "Output file path doesn't match expected"
        
        # Verify ffmpeg was called with the right parameters
        mock_subprocess_run.assert_called_once()
        args, kwargs = mock_subprocess_run.call_args
        
        # Check command arguments
        cmd = args[0]
        assert 'ffmpeg' in cmd[0], "ffmpeg command not called"
        
        # Check for concat mode and input files
        concat_idx = cmd.index('-f') if '-f' in cmd else -1
        assert concat_idx != -1, "No -f concat parameter in ffmpeg command"
        assert cmd[concat_idx + 1] == 'concat', "ffmpeg not using concat format"
        
        # Check for input file list
        input_idx = cmd.index('-i') if '-i' in cmd else -1
        assert input_idx != -1, "No input file specified in command"
        
        # Check output file
        assert str(output_file) in cmd, "Output file not specified in command"
    
    @patch('subprocess.run')
    def test_create_audio_book(self, mock_subprocess_run, test_config):
        """Test creating an audio book from all audio chunks"""
        # Configure the mock
        mock_subprocess_run.return_value = MagicMock(returncode=0)
        
        # Create input files
        input_dir = test_config.audio_chunks_dir
        os.makedirs(input_dir, exist_ok=True)
        
        # Create three dummy audio files
        for i in range(3):
            file_path = input_dir / f"chapter_01{chr(97+i)}.mp3"  # chapter_01a, chapter_01b, chapter_01c
            with open(file_path, 'wb') as f:
                f.write(b"mock audio data")
        
        # Create the concatenator
        concatenator = audio_concatenator.AudioConcatenator(
            input_dir=input_dir,
            output_dir=test_config.audio_book_dir
        )
        
        # Mock concatenate_audio_files to return a predefined output file
        expected_output = test_config.audio_book_dir / "audiobook.mp3"
        with patch.object(
            concatenator, 'concatenate_audio_files', 
            return_value=expected_output
        ) as mock_concatenate:
            result = concatenator.process()
        
        # Check results
        assert result == expected_output, "Result doesn't match expected output file"
        
        # Verify concatenate_audio_files was called with the right parameters
        mock_concatenate.assert_called_once()
        args, kwargs = mock_concatenate.call_args
        
        # Check that audio_files and output_file were passed as arguments
        assert len(args) > 0, "No positional arguments passed"
        audio_files = args[0]
        assert len(audio_files) == 3, "Wrong number of audio files passed"
        assert all(file.parent == input_dir for file in audio_files), "Audio files not from input directory"
        
        # Files should be in order
        expected_filenames = [f"chapter_01{chr(97+i)}.mp3" for i in range(3)]
        actual_filenames = [file.name for file in audio_files]
        assert sorted(actual_filenames) == sorted(expected_filenames), "Audio files not in the expected order"
        
        # Check output file parameter
        assert args[1] == expected_output, "Output file doesn't match expected" 