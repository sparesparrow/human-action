#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Processor adapters for pipeline components
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List
from pathlib import Path

class ProcessorInterface(ABC):
    """Base interface for all processors in the pipeline"""
    
    def __init__(self, config, **kwargs):
        self.config = config
        self.options = kwargs
    
    @abstractmethod
    def process(self) -> Dict[str, Any]:
        """
        Process files and return results
        
        Returns:
            Dictionary with processing results
            {
                "success": bool,
                "files_processed": List[str],
                "stats": Dict[str, Any],
                "error": Optional[str]
            }
        """
        pass

# Adapters for each component (example for PDF Processor)
class PDFProcessor(ProcessorInterface):
    def process(self) -> Dict[str, Any]:
        from pdf_extractor import PDFProcessor as OriginalPDFProcessor
        
        try:
            # Create processor instance with config paths
            processor = OriginalPDFProcessor(
                input_dir=self.config.pdf_dir,
                output_dir=self.config.markdown_chapters_dir
            )
            
            # Process PDFs
            pdf_files = processor.scan_input_directory()
            processed_files = []
            
            for pdf_file in pdf_files:
                result_files = processor.process(pdf_file)
                processed_files.extend([str(f) for f in result_files])
            
            return {
                "success": True,
                "files_processed": processed_files,
                "stats": {"file_count": len(processed_files)}
            }
        except Exception as e:
            return {
                "success": False,
                "files_processed": [],
                "error": str(e)
            } 
# -*- coding: utf-8 -*-

"""
Processor adapters for pipeline components
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List
from pathlib import Path

class ProcessorInterface(ABC):
    """Base interface for all processors in the pipeline"""
    
    def __init__(self, config, **kwargs):
        self.config = config
        self.options = kwargs
    
    @abstractmethod
    def process(self) -> Dict[str, Any]:
        """
        Process files and return results
        
        Returns:
            Dictionary with processing results
            {
                "success": bool,
                "files_processed": List[str],
                "stats": Dict[str, Any],
                "error": Optional[str]
            }
        """
        pass

# Adapters for each component (example for PDF Processor)
class PDFProcessor(ProcessorInterface):
    def process(self) -> Dict[str, Any]:
        from pdf_extractor import PDFProcessor as OriginalPDFProcessor
        
        try:
            # Create processor instance with config paths
            processor = OriginalPDFProcessor(
                input_dir=self.config.pdf_dir,
                output_dir=self.config.markdown_chapters_dir
            )
            
            # Process PDFs
            pdf_files = processor.scan_input_directory()
            processed_files = []
            
            for pdf_file in pdf_files:
                result_files = processor.process(pdf_file)
                processed_files.extend([str(f) for f in result_files])
            
            return {
                "success": True,
                "files_processed": processed_files,
                "stats": {"file_count": len(processed_files)}
            }
        except Exception as e:
            return {
                "success": False,
                "files_processed": [],
                "error": str(e)
            }