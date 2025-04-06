#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Pipeline orchestration with state management for audio book generation
"""

import concurrent.futures
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from config import Config

# Initialize logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("pipeline.log")],
)
logger = logging.getLogger(__name__)


class Pipeline:
    def __init__(self, config_file_or_obj: Union[str, Config] = "config.yaml"):
        """
        Initialize the pipeline with configuration

        Args:
            config_file_or_obj: Either a path to config file or a Config object
        """
        if isinstance(config_file_or_obj, Config):
            self.config = config_file_or_obj
        else:
            self.config = Config(config_file_or_obj)

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
                    "paragraph_separation": {"completed": False, "files_processed": []},
                },
                "last_run": None,
                "stats": {},
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
            self.state["stages"][stage_name]["files_processed"] = results.get(
                "files_processed", []
            )

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

    def run_pipeline(self, start_stage=None, end_stage=None, **kwargs):
        """Run the complete pipeline or a section of it"""
        stages = [
            ("pdf_extraction", PDFProcessor),
            ("chunking", MarkdownChunker),
            ("optimization", BatchProcessor),
            ("audio_generation", AudioGenerator),
            ("audio_concatenation", AudioConcatenator),
            ("paragraph_separation", ParagraphSeparator),
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
            if self.state["stages"][stage_name]["completed"] and not kwargs.get(
                "force", False
            ):
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
                self.state["stages"][stage] = {
                    "completed": False,
                    "files_processed": [],
                }
        else:
            # Reset specific stages
            for stage in stages:
                if stage in self.state["stages"]:
                    self.state["stages"][stage] = {
                        "completed": False,
                        "files_processed": [],
                    }

        self._save_state()
        logger.info(f"Reset state for stages: {stages or 'all'}")

    # New methods to support the test interface

    def process(self, input_file, steps=None, state_file=None):
        """
        Process method that mimics the expected interface for testing

        Args:
            input_file: Path to input PDF file
            steps: List of pipeline steps to run
            state_file: Optional path to state file

        Returns:
            Path to the final output file
        """
        # Set state file path if provided
        if state_file:
            self.state_file = state_file
            # Initialize the state
            if not self.state_file.exists():
                # Create a default state
                self.state = {"input_file": str(input_file), "completed_steps": {}}
                self._save_state()
            else:
                self.state = self._load_state()

        # If we have a list of steps, run those specific steps
        if steps:
            return self.run_pipeline_steps(input_file, steps=steps)

        # Otherwise run the full pipeline
        return self.run_full_pipeline(input_file)

    def run_pipeline_steps(self, input_file, steps=None):
        """
        Run specific steps of the pipeline

        Args:
            input_file: Path to input PDF file
            steps: List of pipeline steps to run

        Returns:
            Path to the final output file
        """
        logger.info(f"Running pipeline steps: {steps}")

        result = None

        # Skip steps that are already completed
        steps_to_run = []
        for step in steps:
            if step not in self.state.get("completed_steps", {}):
                steps_to_run.append(step)

        # Import processors here to avoid circular imports
        import pdf_extractor
        from audio_concatenator import AudioConcatenator
        from chunker_splitter import MarkdownChunker
        from espeak_audio_chunk_generator import EspeakAudioChunkGenerator
        from scripts.separate_paragraphs import ParagraphSeparator

        # Map of step names to processor classes
        processor_map = {
            "pdf_extraction": pdf_extractor.PDFProcessor,
            "chunk_splitting": MarkdownChunker,
            "audio_generation": EspeakAudioChunkGenerator,
            "audio_concatenation": AudioConcatenator,
            "paragraph_separation": ParagraphSeparator,
        }

        # Run each step
        for step in steps_to_run:
            if step in processor_map:
                # Get the processor class
                processor_class = processor_map[step]

                # Initialize the processor
                if step == "pdf_extraction":
                    processor = processor_class()
                    result = processor.process(input_file)
                else:
                    processor = processor_class(
                        self.config.get_path(step + "_input")
                        or self.config.markdown_chunks_dir,
                        self.config.get_path(step + "_output")
                        or self.config.audio_chunks_dir,
                    )
                    result = processor.process()

                # Mark step as completed
                if "completed_steps" not in self.state:
                    self.state["completed_steps"] = {}
                self.state["completed_steps"][step] = {
                    "output_files": (
                        [str(f) for f in result]
                        if isinstance(result, list)
                        else [str(result)]
                    )
                }
                self._save_state()

        # Return the result of the last step
        return result or self.config.audio_book_dir / "audiobook.mp3"

    def run_full_pipeline(self, input_file):
        """
        Run the full pipeline

        Args:
            input_file: Path to input PDF file

        Returns:
            Path to the final output file
        """
        logger.info(f"Running full pipeline for: {input_file}")

        # Run all steps
        steps = [
            "pdf_extraction",
            "chunk_splitting",
            "paragraph_separation",
            "audio_generation",
            "audio_concatenation",
        ]

        return self.run_pipeline_steps(input_file, steps=steps)

    def get_audio_generator(self):
        """
        Get the appropriate audio generator processor
        This method exists for testing to allow mocking
        """
        from espeak_audio_chunk_generator import EspeakAudioChunkGenerator

        return EspeakAudioChunkGenerator(
            self.config.markdown_chunks_dir, self.config.audio_chunks_dir
        )
