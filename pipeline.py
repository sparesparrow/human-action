#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Pipeline orchestration with state management for audio book generation
"""

import os
import json
import logging
from pathlib import Path
from datetime import datetime
import concurrent.futures
from typing import Dict, List, Any, Optional

from config import Config

# Initialize logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('pipeline.log')
    ]
)
logger = logging.getLogger(__name__)

class Pipeline:
    def __init__(self, config_file="config.yaml"):
        """Initialize the pipeline with configuration"""
        self.config = Config(config_file)
        self.state_file = Path("pipeline_state.json")
        self.state = self._load_state()
        
    def _load_state(self) -> Dict:
        """Load pipeline state from JSON file"""
        if not self.state_file.exists():
            return {
                "stages": {
                    "pdf_extraction": {"completed": False, "files_processed": []},
                    "chunking": {"completed": False, "files_processed": []},
                    "optimization": {"completed": False, "files_processed": []},
                    "audio_generation": {"completed": False, "files_processed": []},
                    "audio_concatenation": {"completed": False, "files_processed": []},
                    "paragraph_separation": {"completed": False, "files_processed": []}
                },
                "last_run": None,
                "stats": {}
            }
        
        with open(self.state_file, "r") as f:
            return json.load(f)
    
    def _save_state(self):
        """Save pipeline state to JSON file"""
        self.state["last_run"] = datetime.now().isoformat()
        with open(self.state_file, "w") as f:
            json.dump(self.state, f, indent=2)
    
    def run_stage(self, stage_name: str, processor_class, **kwargs):
        """Run a specific pipeline stage"""
        logger.info(f"Starting stage: {stage_name}")
        
        try:
            # Initialize the processor with config and any extra args
            processor = processor_class(self.config, **kwargs)
            
            # Run the processor and get results
            results = processor.process()
            
            # Update state with processed files
            self.state["stages"][stage_name]["files_processed"] = results.get("files_processed", [])
            
            # Mark as completed if successful
            if results.get("success", False):
                self.state["stages"][stage_name]["completed"] = True
                
            # Store statistics
            self.state["stats"][stage_name] = results.get("stats", {})
            
            # Save updated state
            self._save_state()
            
            logger.info(f"Completed stage: {stage_name}")
            return results
            
        except Exception as e:
            logger.error(f"Error in stage {stage_name}: {str(e)}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def run_pipeline(self, start_stage=None, end_stage=None):
        """Run the complete pipeline or a section of it"""
        stages = [
            ("pdf_extraction", PDFProcessor),
            ("chunking", MarkdownChunker),
            ("optimization", BatchProcessor),
            ("audio_generation", AudioGenerator),
            ("audio_concatenation", AudioConcatenator),
            ("paragraph_separation", ParagraphSeparator)
        ]
        
        # Determine which stages to run
        start_idx = 0
        end_idx = len(stages)
        
        if start_stage:
            for i, (stage_name, _) in enumerate(stages):
                if stage_name == start_stage:
                    start_idx = i
                    break
        
        if end_stage:
            for i, (stage_name, _) in enumerate(stages):
                if stage_name == end_stage:
                    end_idx = i + 1
                    break
        
        # Run the selected stages
        for i in range(start_idx, end_idx):
            stage_name, processor_class = stages[i]
            
            # Skip if already completed and not forced to rerun
            if self.state["stages"][stage_name]["completed"] and not kwargs.get("force", False):
                logger.info(f"Skipping completed stage: {stage_name}")
                continue
            
            result = self.run_stage(stage_name, processor_class)
            
            # Stop pipeline on failure
            if not result.get("success", False):
                logger.error(f"Pipeline stopped due to failure in stage: {stage_name}")
                return False
        
        return True
    
    def reset_state(self, stages=None):
        """Reset pipeline state for all or specific stages"""
        if stages is None:
            # Reset all stages
            for stage in self.state["stages"]:
                self.state["stages"][stage] = {"completed": False, "files_processed": []}
        else:
            # Reset specific stages
            for stage in stages:
                if stage in self.state["stages"]:
                    self.state["stages"][stage] = {"completed": False, "files_processed": []}
        
        self._save_state()
        logger.info(f"Reset state for stages: {stages or 'all'}") 
# -*- coding: utf-8 -*-

"""
Pipeline orchestration with state management for audio book generation
"""

import os
import json
import logging
from pathlib import Path
from datetime import datetime
import concurrent.futures
from typing import Dict, List, Any, Optional

from config import Config

# Initialize logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('pipeline.log')
    ]
)
logger = logging.getLogger(__name__)

class Pipeline:
    def __init__(self, config_file="config.yaml"):
        """Initialize the pipeline with configuration"""
        self.config = Config(config_file)
        self.state_file = Path("pipeline_state.json")
        self.state = self._load_state()
        
    def _load_state(self) -> Dict:
        """Load pipeline state from JSON file"""
        if not self.state_file.exists():
            return {
                "stages": {
                    "pdf_extraction": {"completed": False, "files_processed": []},
                    "chunking": {"completed": False, "files_processed": []},
                    "optimization": {"completed": False, "files_processed": []},
                    "audio_generation": {"completed": False, "files_processed": []},
                    "audio_concatenation": {"completed": False, "files_processed": []},
                    "paragraph_separation": {"completed": False, "files_processed": []}
                },
                "last_run": None,
                "stats": {}
            }
        
        with open(self.state_file, "r") as f:
            return json.load(f)
    
    def _save_state(self):
        """Save pipeline state to JSON file"""
        self.state["last_run"] = datetime.now().isoformat()
        with open(self.state_file, "w") as f:
            json.dump(self.state, f, indent=2)
    
    def run_stage(self, stage_name: str, processor_class, **kwargs):
        """Run a specific pipeline stage"""
        logger.info(f"Starting stage: {stage_name}")
        
        try:
            # Initialize the processor with config and any extra args
            processor = processor_class(self.config, **kwargs)
            
            # Run the processor and get results
            results = processor.process()
            
            # Update state with processed files
            self.state["stages"][stage_name]["files_processed"] = results.get("files_processed", [])
            
            # Mark as completed if successful
            if results.get("success", False):
                self.state["stages"][stage_name]["completed"] = True
                
            # Store statistics
            self.state["stats"][stage_name] = results.get("stats", {})
            
            # Save updated state
            self._save_state()
            
            logger.info(f"Completed stage: {stage_name}")
            return results
            
        except Exception as e:
            logger.error(f"Error in stage {stage_name}: {str(e)}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def run_pipeline(self, start_stage=None, end_stage=None):
        """Run the complete pipeline or a section of it"""
        stages = [
            ("pdf_extraction", PDFProcessor),
            ("chunking", MarkdownChunker),
            ("optimization", BatchProcessor),
            ("audio_generation", AudioGenerator),
            ("audio_concatenation", AudioConcatenator),
            ("paragraph_separation", ParagraphSeparator)
        ]
        
        # Determine which stages to run
        start_idx = 0
        end_idx = len(stages)
        
        if start_stage:
            for i, (stage_name, _) in enumerate(stages):
                if stage_name == start_stage:
                    start_idx = i
                    break
        
        if end_stage:
            for i, (stage_name, _) in enumerate(stages):
                if stage_name == end_stage:
                    end_idx = i + 1
                    break
        
        # Run the selected stages
        for i in range(start_idx, end_idx):
            stage_name, processor_class = stages[i]
            
            # Skip if already completed and not forced to rerun
            if self.state["stages"][stage_name]["completed"] and not kwargs.get("force", False):
                logger.info(f"Skipping completed stage: {stage_name}")
                continue
            
            result = self.run_stage(stage_name, processor_class)
            
            # Stop pipeline on failure
            if not result.get("success", False):
                logger.error(f"Pipeline stopped due to failure in stage: {stage_name}")
                return False
        
        return True
    
    def reset_state(self, stages=None):
        """Reset pipeline state for all or specific stages"""
        if stages is None:
            # Reset all stages
            for stage in self.state["stages"]:
                self.state["stages"][stage] = {"completed": False, "files_processed": []}
        else:
            # Reset specific stages
            for stage in stages:
                if stage in self.state["stages"]:
                    self.state["stages"][stage] = {"completed": False, "files_processed": []}
        
        self._save_state()
        logger.info(f"Reset state for stages: {stages or 'all'}")