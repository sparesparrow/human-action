# Hybrid Quality Audio Synthesis Plan

**Date:** 2024-07-23

**Objective:** Balance audio quality and cost by strategically using both the high-quality ElevenLabs API and the lower-quality Espeak engine for different parts of the content. This aims to maximize user experience on critical sections while minimizing overall generation costs.

## Criteria for ElevenLabs Quality (High Quality - Paid)

ElevenLabs audio should be prioritized for content where high fidelity significantly enhances user experience. Examples include:

-   **Chapter Introductions and Summaries:** Setting the tone and providing clear takeaways.
-   **Key Explanations or Definitions:** Ensuring critical concepts are easily understood.
-   **Dialogue or Character Voices:** Providing distinct and engaging voices if applicable.
-   **High-Impact Narrative Sections:** Sections crucial to the story or main argument.
-   **(Add other specific criteria as needed)**

## Criteria for Espeak Quality (Standard Quality - Free)

Espeak audio can be used for content where standard intelligibility is sufficient and the cost savings are beneficial. Examples include:

-   **Standard Narrative Paragraphs:** Body text connecting key points.
-   **Less Critical Sections:** Background information, extended examples, or supplementary content.
-   **Appendices or Footnotes:** Content referenced but not part of the main flow.
-   **Initial Drafts/Previews:** Generating quick audio previews before finalizing with ElevenLabs.
-   **(Add other specific criteria as needed)**

## Chapter/Section Allocation Strategy

The allocation will be determined on a chapter-by-chapter basis prior to generation. The process involves:

1.  Reviewing the content of each chapter scheduled in `next-chapter-audio-plan.md`.
2.  Identifying sections matching the ElevenLabs criteria.
3.  Identifying sections suitable for Espeak criteria.
4.  Documenting the allocation (potentially in a separate file or table linked here) for the generation scripts.

**Example Allocation (Placeholder for Chapter X):**

-   `paragraph_001.md` (Intro): ElevenLabs
-   `paragraph_002.md` (Narrative): Espeak
-   `paragraph_003.md` (Key Definition): ElevenLabs
-   `paragraph_004.md` (Narrative): Espeak
-   ...
-   `paragraph_025.md` (Summary): ElevenLabs

## Workflow Implementation

1.  **Planning:** Update `next-chapter-audio-plan.md` with the list of chapters for the next batch. Separately, define the ElevenLabs vs. Espeak allocation for paragraphs within those chapters.
2.  **ElevenLabs Generation:** Execute an ElevenLabs generation script targeting only the designated high-quality paragraphs for the planned chapters. Place outputs in a specific directory (e.g., `data/5-audio-chunks-elevenlabs/`).
3.  **Espeak Generation:** Execute the Espeak generation script (e.g., `generate_espeak_audio.py` or similar, potentially adapted) targeting the remaining designated standard-quality paragraphs for the planned chapters. Place outputs in the Espeak directory (e.g., `data/5-audio-chunks-espeak/`).
4.  **Concatenation:** Use a modified concatenation script (e.g., `audio_concatenator.py`) that can pull chunks from *both* the ElevenLabs and Espeak directories in the correct order for each chapter, based on the allocation plan.
5.  **Output:** Place the final, mixed-quality chapter audio files in the main output directory (`data/6-audio-chapters/`).
6.  **Verification:** Review the final audio chapters for correct sequencing and acceptable quality transitions.

**Note:** This plan requires modifications to the existing generation and concatenation scripts to handle the paragraph-level quality allocation and sourcing from multiple chunk directories. 