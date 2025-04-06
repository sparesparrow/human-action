# Next Chapter Audio Synthesis Plan

**Date:** 2024-07-23

**Objective:** Outline the chapters to be included in the next audio synthesis batch using the configured TTS engine.

## Chapters for Next Batch

The following chapter directories from `data/7-paragraphs/text/` are scheduled for the next audio generation process:

- chapter_13/
- chapter_16/
- chapter_18/
- chapter_19/
- chapter_21/
- chapter_22/
- chapter_24/
- chapter_25/
- chapter_26/
- chapter_27/
- chapter_29/
- chapter_30/
- chapter_32/
- chapter_33/
- chapter_35/
- chapter_36/
- chapter_37/
- chapter_39/
- chapter_42/
- chapter_44/
- chapter_46/
- chapter_47/
- chapter_48/
- chapter_54/
- chapter_55/
- chapter_56/
- chapter_57/
- chapter_58/
- chapter_60/
- chapter_61/
- chapter_63/
- chapter_65/
- chapter_66/
- chapter_67/
- chapter_68/
- chapter_69/
- chapter_71/
- chapter_72/
- chapter_73/
- chapter_75/
- chapter_78/
- chapter_79/
- chapter_80/
- chapter_81/
- chapter_82/
- chapter_83/
- chapter_85/
- chapter_86/
- chapter_87/
- chapter_88/
- chapter_89/
- chapter_90/
- chapter_93/
- chapter_94/
- chapter_95/
- chapter_96/
- chapter_99/
- chapter_100/
- chapter_103/
- chapter_104/
- chapter_107/
- chapter_108/
- chapter_109/
- chapter_110/
- chapter_111/
- chapter_112/
- chapter_119/
- chapter_125/
- chapter_126/
- chapter_130/
- chapter_131/
- chapter_133/
- chapter_137/
- chapter_139/
- chapter_140/
- chapter_142/
- chapter_145/
- chapter_147/
- chapter_148/
- chapter_150/
- chapter_152/
- chapter_154/
- chapter_155/
- chapter_156/
- chapter_159/
- chapter_161/
- chapter_162/
- chapter_163/
- chapter_164/
- chapter_165/
- chapter_167/
- chapter_168/
- chapter_169/
- chapter_170/
- chapter_172/
- chapter_176/
- chapter_178/
- chapter_183/
- chapter_184/

## Processing Instructions

1.  Ensure the paragraph markdown files within the chapter directories listed above are ready for processing.
2.  Use the configured TTS engine (currently Espeak, potentially ElevenLabs later) to generate audio for each paragraph within these chapters.
3.  Concatenate paragraph audio files for each chapter and place the final chapter audio files (e.g., `13-Chapter_13.mp3`) into the appropriate output directory (e.g., `data/6-audio-chapters/`).
4.  Verify the quality and completeness of the generated audio files.