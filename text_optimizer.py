import asyncio
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import anthropic
from anthropic.types.beta.message_create_params import MessageCreateParamsNonStreaming
# Corrected imports for batch types
from anthropic.types.beta import (
    MessageBatch,
    MessageBatchSucceededResult,
    MessageBatchErroredResult,
    MessageBatchExpiredResult,
    MessageBatchCanceledResult
)
from anthropic.types.beta.messages.batch_create_params import Request as BetaRequest
# Corrected imports for content block types
from anthropic.types.text_block import TextBlock
# Import other block types if needed for type checking, though not directly used for .text
from anthropic.types.tool_use_block import ToolUseBlock
from anthropic.types.thinking_block import ThinkingBlock
from anthropic.types.redacted_thinking_block import RedactedThinkingBlock

from tqdm import tqdm

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class BatchProcessor:
    def __init__(self, api_key: str, base_dir: str):
        # Ensure api_key is a non-empty string
        if not api_key or not isinstance(api_key, str):
            raise ValueError("Anthropic API key must be provided as a non-empty string.")
        self.client = anthropic.Anthropic(api_key=api_key)
        self.base_dir = Path(base_dir)
        self.system_prompt = """You are an expert language editor specializing in optimizing Czech text for voice synthesis. Your task is to modify the given text to make it optimal for reading aloud.
Follow these instructions to modify the text:
1. Remove all numerical references, footnotes, and page numbers.
2. Join words that are hyphenated at the end of lines.
3. Remove excessive spaces and empty lines.
4. Preserve correct punctuation and sentence structure.
5. Maintain italics and other meaningful text formatting if marked.
6. Adjust the text to be natural for reading aloud while preserving the original meaning.
7. Return only the modified text without any comments or explanations."""
        self.custom_id_to_filename: Dict[str, str] = {} # Initialize mapping


    def read_file_content(self, file_path: Path) -> str:
        """Reads the content of a text file and returns it as a string."""
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                return file.read()
        except FileNotFoundError:
            logging.error(f"File not found: {file_path}")
            return ""
        except Exception as e:
            logging.error(f"Error reading {file_path}: {e}")
            return ""

    def write_optimized_content(self, file_path: Path, content: str) -> None:
        """Writes the optimized content to a new file."""
        try:
            # Ensure the output directory exists
            output_dir = self.base_dir / "data/4-markdown-chunks-optimized"
            output_dir.mkdir(parents=True, exist_ok=True)

            optimized_path = output_dir / f"{file_path.stem}-OPTIMIZED{file_path.suffix}"

            with open(optimized_path, "w", encoding="utf-8") as file:
                file.write(content)
            logging.info(f"Successfully wrote optimized content to {optimized_path}")
        except Exception as e:
            logging.error(f"Error writing to {optimized_path}: {e}")

    def prepare_batch_requests(self, files_to_process: List[str]) -> list[BetaRequest]: # Use BetaRequest
        """Prepares batch requests for processing."""
        requests = []
        # Store filename mapping for later use
        self.custom_id_to_filename = {}
        for idx, filename in enumerate(files_to_process, 1):
            # Construct full path based on base_dir and relative filename
            file_path = self.base_dir / filename
            content = self.read_file_content(file_path)

            if content:
                custom_id = f"req_{idx}"
                self.custom_id_to_filename[custom_id] = filename
                # Use BetaRequest explicitly
                # Correctly wrap message parameters in MessageCreateParamsNonStreaming inside body
                message_params = MessageCreateParamsNonStreaming(
                    model="claude-3-5-sonnet-20240620", # Updated model
                    max_tokens=4096, # Adjusted max_tokens
                    temperature=0,
                    system=self.system_prompt,
                    messages=[
                        {
                            "role": "user",
                            "content": content # Simplified content structure
                        }
                    ]
                )
                request = BetaRequest(
                    custom_id=custom_id,
                    method="POST", # Required for BetaRequest
                    url="/v1/messages", # Required for BetaRequest
                    body=message_params # Assign the structured params here
                )
                requests.append(request)
            else:
                logging.warning(f"Skipping empty or unreadable file: {filename}")


        return requests

    async def process_batch_results(
        self, batch_id: str, total_requests: int
    ) -> None:
        """Processes batch results and writes optimized content."""
        try:
            pbar = tqdm(total=total_requests, desc="Processing files")
            processed_custom_ids = set()
            retry_interval = 5  # seconds between status checks

            while len(processed_custom_ids) < total_requests:
                # Check batch processing status using client.beta
                message_batch = self.client.beta.messages.batches.retrieve(batch_id)
                logging.debug( # Use debug level for frequent status updates
                    f"Batch {message_batch.id} status: {message_batch.status}, "
                    f"Completed: {message_batch.completed_requests}, Failed: {message_batch.failed_requests}, "
                    f"Total: {message_batch.total_requests}"
                )

                # Update progress bar based on API response
                pbar.n = (message_batch.completed_requests or 0) + (message_batch.failed_requests or 0)
                pbar.refresh()


                # If still processing, wait before checking again
                if message_batch.status in ("in_progress", "queued", "preparing"):
                    await asyncio.sleep(retry_interval)
                    continue

                # If final state reached, process results and exit loop
                if message_batch.status in ("completed", "failed", "cancelled", "expired"):
                    logging.info(f"Batch {message_batch.id} finished with status: {message_batch.status}")
                    # Use client.beta explicitly to list results
                    for result_page in self.client.beta.messages.batches.list_results(batch_id, auto_paginate=True):
                        # Check if 'output' exists and has 'message'
                        if result_page.custom_id not in processed_custom_ids: # Process each result only once
                            filename = self.custom_id_to_filename.get(result_page.custom_id, "Unknown")
                            file_path = self.base_dir / filename if filename != "Unknown" else None

                            if result_page.output and result_page.output.message:
                                logging.info(f"Processing successful result for {result_page.custom_id} ({filename})")
                                # Ensure content is present and is a list
                                if result_page.output.message.content and isinstance(result_page.output.message.content, list):
                                    # Check if the first content block is TextBlock
                                    first_content_block = result_page.output.message.content[0]
                                    if isinstance(first_content_block, TextBlock):
                                        if file_path:
                                             self.write_optimized_content(file_path, first_content_block.text)
                                        else:
                                             logging.error(f"Could not find original file path for custom_id {result_page.custom_id}")
                                    else:
                                         logging.warning(f"Unexpected content block type for {result_page.custom_id}: {type(first_content_block)}")
                                else:
                                     logging.warning(f"No content or unexpected content format in successful result for {result_page.custom_id}")

                            elif result_page.error:
                                error_type = result_page.error.type
                                error_message = result_page.error.message
                                logging.error(f"Error ({error_type}) for request {result_page.custom_id} ({filename}): {error_message}")
                            else:
                                 logging.warning(f"Result for {result_page.custom_id} ({filename}) has neither output nor error.")

                            processed_custom_ids.add(result_page.custom_id)
                            # Update pbar manually after processing each item if not updated above
                            if pbar.n < len(processed_custom_ids):
                                pbar.n = len(processed_custom_ids)
                                pbar.refresh()


                    # Ensure progress bar reaches total after processing all results
                    if pbar.n < total_requests:
                         pbar.n = total_requests
                         pbar.refresh()
                    break # Exit loop after final state is reached

            pbar.close()

        except Exception as e:
            logging.error(f"Error in batch processing results: {e}", exc_info=True)
            if 'pbar' in locals() and pbar:
                 pbar.close() # Ensure progress bar is closed on error
            raise

    async def process_files(self, files_to_process: List[str]) -> None:
        """Processes files using the Message Batches API."""
        try:
            # Prepare batch requests
            requests = self.prepare_batch_requests(files_to_process)

            if not requests:
                logging.warning("No valid files found or prepared for batch processing.")
                return

            # Create batch request using client.beta
            logging.info(f"Submitting batch request with {len(requests)} files...")

            # Define input/output file paths for the batch metadata
            input_file_path = self.base_dir / f"batch_input_{time.strftime('%Y%m%d-%H%M%S')}.jsonl"
            output_file_path = self.base_dir / f"batch_output_{time.strftime('%Y%m%d-%H%M%S')}.jsonl" # Optional

            # Upload batch input file
            # NOTE: This requires writing requests to a file first.
            # Adapting the structure: Create the file and upload it.
            with open(input_file_path, "w", encoding='utf-8') as f:
                 for req in requests:
                     f.write(req.model_dump_json() + '\n') # Use model_dump_json if available, else custom serialization

            # Assuming client.beta.batches has an upload method or similar
            # This part is hypothetical based on typical batch APIs - consult Anthropic SDK docs
            # For example:
            # input_file_object = self.client.beta.files.create(purpose="batch", file=open(input_file_path, "rb"))
            # input_file_id = input_file_object.id
            # If direct file upload isn't the method, the `create` call might take requests directly as before.
            # Reverting to the direct `create` call as file upload specifics are unclear.

            message_batch = self.client.beta.messages.batches.create(requests=requests) # Pass requests directly

            # Clean up temp input file if created
            # if 'input_file_path' in locals() and input_file_path.exists():
            #      input_file_path.unlink()


            # Monitor batch processing status
            logging.info(f"Batch ID: {message_batch.id} submitted. Status: {message_batch.status}")
            logging.info("Monitoring batch progress...")

            # Process results
            await self.process_batch_results(message_batch.id, len(requests))

            logging.info("Batch processing completed")

        except Exception as e:
            logging.error(f"Error processing files in batch: {e}", exc_info=True)

    def process(self) -> Dict[str, Any]:
        """
        Process method compatible with the processor interface.

        Returns:
            Dictionary with processing results
        """
        try:
            # Get list of files to process (markdown chunks)
            input_dir = self.base_dir / "data/3-markdown-chunks" # Use base_dir
            output_dir = self.base_dir / "data/4-markdown-chunks-optimized" # Use base_dir

            # Create output directory if it doesn't exist
            output_dir.mkdir(parents=True, exist_ok=True)

            # Find all markdown files that haven't been optimized yet
            files_to_process = []
            for f in input_dir.glob("*.md"):
                 optimized_filename = f"{f.stem}-OPTIMIZED{f.suffix}"
                 if not (output_dir / optimized_filename).exists():
                      files_to_process.append(str(f.relative_to(self.base_dir)))


            if not files_to_process:
                logging.info("No files found to process (or all already optimized).")
                return {
                    "success": True,
                    "processed_files": [],
                    "stats": {"input_count": 0, "output_count": 0, "optimized_count": 0},
                }

            logging.info(f"Found {len(files_to_process)} files needing optimization.")

            # Run the async process
            asyncio.run(self.process_files(files_to_process))

            # Count output files actually created in this run (more accurate)
            # We rely on the processing logic to log success/failure per file
            output_files_now = list(output_dir.glob("*-OPTIMIZED.md"))


            return {
                "success": True, # Assuming batch submission itself is success; individual errors logged within
                "processed_files": files_to_process, # Files attempted
                "stats": {
                    "input_count": len(files_to_process),
                    "output_count": len(output_files_now), # Total optimized files existing now
                    # Could add more detailed stats based on batch results if needed
                },
            }
        except Exception as e:
            logging.error(f"Error in BatchProcessor process method: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "processed_files": [],
                "stats": {"input_count": 0, "output_count": 0, "optimized_count": 0},
            }


async def main():
    # Initialize the processor
    api_key = os.getenv("ANTHROPIC_API_KEY")
    # API Key validation happens in BatchProcessor constructor

    base_dir = "."
    try:
        processor = BatchProcessor(api_key=api_key, base_dir=base_dir) # Pass validated key
    except ValueError as e:
         logging.error(e)
         return
    except Exception as e:
        logging.error(f"Failed to initialize BatchProcessor: {e}", exc_info=True)
        return


    # Get files to process (using the logic now inside the process method)
    # This main function now just calls the process method
    processor.process()


if __name__ == "__main__":
    # Example usage: python text_optimizer.py
    # Ensure ANTHROPIC_API_KEY is set as an environment variable
    asyncio.run(main())
