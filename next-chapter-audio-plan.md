# Next Chapter Audio Synthesis Plan

**Date:** 2024-04-06

**Objective:** Outline the chapters to be included in the next audio synthesis batch using the ElevenLabs API (or current TTS engine).

## Chapters for Next Batch

The following markdown chapter files from `data/2-markdown-chapters/` are scheduled for the next audio generation process:

- chapter_187.md
- chapter_188.md
- chapter_189.md
- chapter_190.md
- chapter_191.md
- chapter_192.md

## Processing Instructions

1.  Ensure the markdown files listed above are pre-processed and optimized if necessary (e.g., using `text_optimizer.py`).
2.  Use the configured TTS engine (currently Espeak, potentially ElevenLabs later) to generate audio for each chapter.
3.  Place the generated audio files (e.g., `187-Chapter_187.mp3`) into the appropriate output directory (e.g., `data/6-audio-chapters-espeak/`).
4.  Verify the quality and completeness of the generated audio files. 