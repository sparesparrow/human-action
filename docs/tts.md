# LidskeJednani Audio Processing Tools

This repository contains tools for processing text files into audio files for the "Lidské jednání" (Human Action) project.

## Requirements

- Python 3.6+
- ElevenLabs API key
- Required Python packages: `elevenlabs`
- ffmpeg (for audio concatenation)

Install the required packages:

```bash
pip install elevenlabs
```

Make sure ffmpeg is installed:

```bash
# On Ubuntu/Debian
sudo apt-get install ffmpeg

# On macOS with Homebrew
brew install ffmpeg
```

## Scripts

### 1. Simple TTS Processor (`audio_chunk_generator.py`)

This script processes a single markdown file to generate an audio file using the ElevenLabs API.

#### Usage

```bash
python audio_chunk_generator.py path/to/markdown/file.md [options]
```

#### Options

- `-o, --output-dir`: Output directory for audio files (default: `data/5-audio-chunks`)
- `-v, --voice-id`: ID of the ElevenLabs voice to use (default: Czech voice)
- `-m, --model-id`: ID of the ElevenLabs model to use (default: multilingual model)
- `--stability`: Voice stability (0.0-1.0) (default: 0.5)
- `--similarity-boost`: Voice similarity boost (0.0-1.0) (default: 0.75)
- `--style`: Voice style (0.0-1.0) (default: 0.0)
- `--api-key`: ElevenLabs API key (defaults to ELEVENLABS_API_KEY environment variable)

#### Example

```bash
export ELEVENLABS_API_KEY="your_api_key_here"
python audio_chunk_generator.py data/4-markdown-chunks-optimized/chapter_30a-OPTIMIZED.md
```

This will:
1. Convert the markdown file to audio using ElevenLabs
2. Save the audio file as `chapter_30a.mp3` in the `data/5-audio-chunks` directory
3. Rename the processed markdown file to `AUDIO_GENERATED-chapter_30a-OPTIMIZED.md`

### 2. Audio Concatenation Tool (`audio_concat.py`)

This script concatenates individual audio files into complete chapter files using ffmpeg.

#### Usage

```bash
python audio_concat.py [options]
```

#### Options

- `-i, --input-dir`: Input directory containing audio chunks (default: `data/5-audio-chunks`)
- `-o, --output-dir`: Output directory for concatenated chapters (default: `data/6-audio-chapters`)
- `-c, --chapter`: Process only a specific chapter number (e.g., "01")

#### Example

```bash
# Process all chapters
python audio_concat.py

# Process only chapter 1
python audio_concat.py -c 01
```

## Workflow

1. Generate individual audio files for markdown chunks:
   ```bash
   python audio_chunk_generator.py data/4-markdown-chunks-optimized/chapter_30a-OPTIMIZED.md
   ```

2. After generating all audio chunks for a chapter, concatenate them into a complete chapter:
   ```bash
   python audio_concat.py -c 30
   ```

   Or concatenate all available chapters:
   ```bash
   python audio_concat.py
   ```

## Note
