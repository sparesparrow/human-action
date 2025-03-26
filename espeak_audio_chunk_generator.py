import os
import subprocess
from pathlib import Path

class EspeakAudioChunkGenerator:
    """
    Audio generator that uses espeak instead of ElevenLabs for testing purposes.
    This is a cost-free alternative for testing the audio generation pipeline.
    """
    
    def __init__(self, input_dir, output_dir, language="cs"):
        """
        Initialize the espeak audio generator.
        
        Args:
            input_dir: Directory containing markdown chunks to synthesize.
            output_dir: Directory to save generated audio files.
            language: Language code for espeak voice (default: cs for Czech).
        """
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.language = language
        
        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)
    
    def synthesize_chunk(self, input_file):
        """
        Synthesize a single chunk using espeak.
        
        Args:
            input_file: Path to markdown file to synthesize.
            
        Returns:
            Path to the generated audio file.
        """
        # Get the stem name from the input file (without extension)
        base_name = Path(input_file).stem
        output_file = self.output_dir / f"{base_name}.mp3"
        
        # Read the markdown content
        with open(input_file, 'r', encoding='utf-8') as f:
            text = f.read()
        
        # Use espeak to generate audio
        # Using --stdout to pipe the audio data directly to a file
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
        """
        Process all markdown files in the input directory.
        
        Args:
            directory: Optional override for input directory.
            
        Returns:
            List of paths to generated audio files.
        """
        directory = directory or self.input_dir
        input_files = sorted(list(Path(directory).glob('*.md')))
        
        output_files = []
        for input_file in input_files:
            output_file = self.synthesize_chunk(input_file)
            output_files.append(output_file)
            
        return output_files 