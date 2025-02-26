#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
PDF Processor for Lidské Jednání Project
---------------------------------------

Extracts text from PDF files and creates markdown chapter files.
Input: PDF file from data/1-pdf
Output: Markdown chapter files in data/2-markdown-chapters
"""

import os
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
        logging.FileHandler('pdf_processing.log')
    ]
)
logger = logging.getLogger(__name__)

class PDFProcessor:
    """Extracts text from PDF files and creates markdown chapter files."""
    
    def __init__(self, input_dir: str = "/home/sparrow/projects/LidskeJednani/data/1-pdf", 
                 output_dir: str = "/home/sparrow/projects/LidskeJednani/data/2-markdown-chapters"):
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
        # This is a placeholder for the actual implementation
        logger.info(f"Extracting text from {pdf_path}")
        return f"Placeholder text extracted from {pdf_path.name}"
    
    def detect_chapters(self, text: str) -> List[Dict[str, Any]]:
        """
        Detect chapters in the extracted text.
        
        Args:
            text: Extracted text from PDF
            
        Returns:
            List of chapters with their content
        """
        # TODO: Implement chapter detection
        # This is a placeholder for the actual implementation
        logger.info("Detecting chapters in the text")
        self.chapters = [
            {"number": 1, "title": "Chapter 1", "content": "Content of chapter 1"},
            {"number": 2, "title": "Chapter 2", "content": "Content of chapter 2"},
        ]
        return self.chapters
    
    def save_chapters(self) -> List[Path]:
        """
        Save chapters to markdown files.
        
        Returns:
            List of saved chapter file paths
        """
        saved_files = []
        for chapter in self.chapters:
            filename = f"chapter_{chapter['number']:02d}.md"
            file_path = self.output_dir / filename
            
            # TODO: Implement proper file writing
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(f"# {chapter['title']}\n\n{chapter['content']}")
            
            saved_files.append(file_path)
            logger.info(f"Saved chapter {chapter['number']} to {file_path}")
        
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
        description='Extract text from PDF and create markdown chapter files'
    )
    
    parser.add_argument(
        '-i', '--input-dir',
        type=str,
        default="/home/sparrow/projects/LidskeJednani/data/1-pdf",
        help='Directory containing PDF files'
    )
    
    parser.add_argument(
        '-o', '--output-dir',
        type=str,
        default="/home/sparrow/projects/LidskeJednani/data/2-markdown-chapters",
        help='Directory for output markdown chapters'
    )
    
    parser.add_argument(
        '-f', '--file',
        type=str,
        help='Specific PDF file to process (optional)'
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
