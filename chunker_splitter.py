#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Markdown Chunker for Lidské Jednání Project
------------------------------------------

Splits markdown chapter files into smaller chunks.
Input: Markdown chapters from data/2-markdown-chapters
Output: Markdown chunks in data/3-markdown-chunks
"""

import os
import re
import logging
import argparse
from pathlib import Path
from typing import List, Dict, Optional, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('markdown_chunking.log')
    ]
)
logger = logging.getLogger(__name__)

class MarkdownChunker:
    """Splits markdown chapter files into smaller chunks."""
    
    def __init__(self, input_dir: str = "/home/sparrow/projects/LidskeJednani/data/2-markdown-chapters", 
                 output_dir: str = "/home/sparrow/projects/LidskeJednani/data/3-markdown-chunks",
                 max_chunk_size: int = 5000):
        """
        Initialize the Markdown Chunker.
        
        Args:
            input_dir: Directory containing markdown chapter files
            output_dir: Directory for output markdown chunks
            max_chunk_size: Maximum size of each chunk in characters
        """
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.max_chunk_size = max_chunk_size
        
        # Create output directory if it doesn't exist
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize state
        self.markdown_files = []
        self.chunks = {}  # Map of chapter to list of chunks
    
    def scan_input_directory(self) -> List[Path]:
        """
        Scan the input directory for markdown chapter files.
        
        Returns:
            List of markdown file paths
        """
        self.markdown_files = sorted(list(self.input_dir.glob("chapter_*.md")))
        logger.info(f"Found {len(self.markdown_files)} markdown chapter files in {self.input_dir}")
        return self.markdown_files
    
    def read_markdown_file(self, file_path: Path) -> str:
        """
        Read a markdown file.
        
        Args:
            file_path: Path to the markdown file
            
        Returns:
            Content of the markdown file
        """
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    
    def split_into_chunks(self, content: str, chapter_num: int) -> List[str]:
        """
        Split markdown content into chunks of specified maximum size.
        
        Args:
            content: Markdown content
            chapter_num: Chapter number for naming chunks
            
        Returns:
            List of chunks
        """
        # TODO: Implement intelligent text splitting
        # This is a placeholder for the actual implementation
        
        # For now, simply split by max_chunk_size, preserving paragraphs
        paragraphs = content.split("\n\n")
        chunks = []
        current_chunk = ""
        
        for paragraph in paragraphs:
            # If adding this paragraph would exceed the max size and we already
            # have content, start a new chunk
            if len(current_chunk) + len(paragraph) > self.max_chunk_size and current_chunk:
                chunks.append(current_chunk)
                current_chunk = paragraph + "\n\n"
            else:
                current_chunk += paragraph + "\n\n"
        
        # Add the last chunk if it's not empty
        if current_chunk:
            chunks.append(current_chunk)
        
        # Store chunks for this chapter
        self.chunks[chapter_num] = chunks
        logger.info(f"Split chapter {chapter_num} into {len(chunks)} chunks")
        
        return chunks
    
    def save_chunks(self, chapter_num: int) -> List[Path]:
        """
        Save chunks to files.
        
        Args:
            chapter_num: Chapter number
            
        Returns:
            List of saved chunk file paths
        """
        saved_files = []
        chapter_chunks = self.chunks.get(chapter_num, [])
        
        for i, chunk in enumerate(chapter_chunks):
            # Use lowercase letter as suffix (a, b, c, etc.)
            suffix = chr(97 + i)  # 97 is ASCII for 'a'
            filename = f"chapter_{chapter_num:02d}{suffix}.md"
            file_path = self.output_dir / filename
            
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(chunk)
            
            saved_files.append(file_path)
            logger.info(f"Saved chunk {i+1}/{len(chapter_chunks)} of chapter {chapter_num} to {file_path}")
        
        return saved_files
    
    def process_file(self, file_path: Path) -> List[Path]:
        """
        Process a single markdown file and split it into chunks.
        
        Args:
            file_path: Path to the markdown file
            
        Returns:
            List of paths to the generated chunk files
        """
        # Extract chapter number from filename (e.g., chapter_01.md -> 1)
        match = re.match(r'chapter_(\d+)\.md', file_path.name)
        if not match:
            logger.warning(f"Could not extract chapter number from {file_path.name}, skipping")
            return []
        
        chapter_num = int(match.group(1))
        
        # Read markdown file
        content = self.read_markdown_file(file_path)
        
        # Split into chunks
        self.split_into_chunks(content, chapter_num)
        
        # Save chunks to files
        return self.save_chunks(chapter_num)
    
    def process_all(self) -> Dict[int, List[Path]]:
        """
        Process all markdown files in the input directory.
        
        Returns:
            Dictionary mapping chapter numbers to lists of chunk file paths
        """
        self.scan_input_directory()
        result = {}
        
        for file_path in self.markdown_files:
            # Extract chapter number
            match = re.match(r'chapter_(\d+)\.md', file_path.name)
            if not match:
                continue
                
            chapter_num = int(match.group(1))
            chunk_files = self.process_file(file_path)
            result[chapter_num] = chunk_files
        
        return result
        
    def process(self) -> List[Path]:
        """
        Process method that will be called from the Pipeline.
        Processes all markdown files and returns a flat list of all chunk files.
        
        Returns:
            List of all chunk file paths
        """
        result = self.process_all()
        # Flatten the dictionary of results into a single list
        all_files = []
        for chapter_files in result.values():
            all_files.extend(chapter_files)
        return all_files


def main():
    """Main function to run the Markdown Chunker from command line."""
    parser = argparse.ArgumentParser(
        description='Split markdown chapter files into smaller chunks'
    )
    
    parser.add_argument(
        '-i', '--input-dir',
        type=str,
        default="/home/sparrow/projects/LidskeJednani/data/2-markdown-chapters",
        help='Directory containing markdown chapter files'
    )
    
    parser.add_argument(
        '-o', '--output-dir',
        type=str,
        default="/home/sparrow/projects/LidskeJednani/data/3-markdown-chunks",
        help='Directory for output markdown chunks'
    )
    
    parser.add_argument(
        '-s', '--size',
        type=int,
        default=5000,
        help='Maximum size of each chunk in characters'
    )
    
    parser.add_argument(
        '-f', '--file',
        type=str,
        help='Specific markdown file to process (optional)'
    )
    
    args = parser.parse_args()
    
    try:
        chunker = MarkdownChunker(args.input_dir, args.output_dir, args.size)
        
        if args.file:
            file_path = Path(args.file)
            if not file_path.exists():
                logger.error(f"File not found: {file_path}")
                return
            chunker.process_file(file_path)
        else:
            chunker.process_all()
            
    except Exception as e:
        logger.error(f"Error chunking markdown: {str(e)}")


if __name__ == "__main__":
    main()
