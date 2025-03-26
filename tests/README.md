# Tests for Human Action Audiobook Generator

This directory contains tests for the Human Action audiobook generator pipeline.

## Structure

- `unit/`: Unit tests for individual components
  - `test_pdf_extractor.py`: Tests for the PDF extraction module
  - `test_chunker_splitter.py`: Tests for the chunk splitting module 
  - `test_espeak_audio_generator.py`: Tests for the audio generator module (using espeak)
  - `test_audio_concatenator.py`: Tests for the audio concatenation module
  - `test_paragraph_separator.py`: Tests for the paragraph separation script
  
- `integration/`: Integration tests for the full pipeline
  - `test_pipeline.py`: Tests for the end-to-end pipeline processing
  
- `fixtures/`: Test data files
  - `sample.md`: A sample markdown file for testing

- `conftest.py`: Pytest configuration, fixtures, and setup

## Running Tests

### Using the test script

The easiest way to run the tests is using the provided script:

```bash
# Run all tests
./run_tests.py

# Run only unit tests
./run_tests.py --unit

# Run only integration tests
./run_tests.py --integration

# Run with verbose output
./run_tests.py -v
```

### Using pytest directly

You can also run the tests directly with pytest:

```bash
# Run all tests
pytest tests/

# Run unit tests
pytest tests/unit/

# Run integration tests
pytest tests/integration/

# Run a specific test file
pytest tests/unit/test_pdf_extractor.py
```

## Cost-Saving Measures

The tests are designed to avoid using APIs that incur costs:

1. **ElevenLabs API**: We use `espeak` instead of ElevenLabs for audio synthesis
2. **Anthropic API**: We skip testing the `text_optimizer.py` module

These substitutions are controlled by environment variables:
- `USE_ESPEAK=1`: Use espeak instead of ElevenLabs
- `SKIP_TEXT_OPTIMIZATION=1`: Skip Anthropic API calls

The `run_tests.py` script sets these environment variables automatically.

## Adding New Tests

When adding new tests:

1. Follow the existing structure
2. Avoid adding dependencies on paid APIs
3. Use mocking for external services
4. Ensure tests are isolated and don't depend on each other
5. Keep test fixtures small and focused 