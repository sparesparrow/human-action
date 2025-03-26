# Lidské Jednání Project / Projekt Lidské Jednání

## Overview / Přehled

Tento projekt zpracovává český překlad knihy "Human Action" (Lidské Jednání) z formátu PDF do optimalizovaných zvukových souborů prostřednictvím série kroků zpracování. Kódová základna obsahuje několik modulů, které zpracovávají různé aspekty zpracovatelského řetězce.

This project processes the Czech translation of the book "Human Action" (Lidské Jednání) from PDF format into optimized audio files through a series of processing steps. The codebase includes several modules that handle different aspects of the processing pipeline.

## STAV
- Textová data připravena: [4-markdown-chunks-optimized](./data/4-markdown-chunks-optimized)
- TODO: dokončit generování všech kapitol
  - `python audio_chunk_generator.py data/4-markdown-chunks-optimized/chapter_XX-OPTIMIZED.md` (ElevenLabs)
  - nebo `python espeak_audio_chunk_generator.py data/4-markdown-chunks-optimized/chapter_XX-OPTIMIZED.md` (espeak-ng)
  - nebo hromadně `./generate_espeak_audio.sh` (zpracuje všechny zbývající soubory pomocí espeak-ng)
- Regularly publishing to [youtube](https://youtube.com/playlist?list=PLaWOvDBjg6WiUcQm-yEP1RskMfPeWMKTL)

## New Architecture / Nová architektura

The project now features a unified pipeline architecture with:

- **Centralized configuration** using `config.py` and `config.yaml`
- **Integrated command-line interface** for running the entire pipeline
- **State tracking** to monitor progress and resume interrupted processing
- **Processor adapters** for consistent interfacing between modules
- **Parallel processing** capabilities for performance optimization

### Command-line Interface / Příkazový řádek

```bash
# Run the complete pipeline
python cli.py run

# Run only a specific part of the pipeline
python cli.py run --start chunking --end audio_generation

# Force reprocessing of already completed stages
python cli.py run --force

# Check pipeline status
python cli.py status

# Reset pipeline state
python cli.py reset
python cli.py reset --stages pdf_extraction chunking
```

## Setup / Nastavení

### Requirements / Požadavky

- Python 3.8+
- ffmpeg (for audio manipulation)
- espeak-ng (for open-source TTS alternative)
- API keys for:
  - Anthropic Claude API (text optimization)
  - ElevenLabs API (text-to-speech)

### Installation / Instalace

```bash
# Clone the repository / Klonování repozitáře
git clone https://github.com/sparesparrow/human-action.git
cd human-action

# Create and activate virtual environment / Vytvoření a aktivace virtuálního prostředí
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies / Instalace závislostí
pip install -r requirements.txt

# Install system dependencies (Ubuntu/Debian)
sudo apt-get install ffmpeg espeak-ng

# Or on macOS
brew install ffmpeg espeak-ng
```

### Environment Setup / Nastavení prostředí

Create a `.env` file in the root directory with your API keys:

```
ANTHROPIC_API_KEY=your_anthropic_api_key
ELEVENLABS_API_KEY=your_elevenlabs_api_key
```

### Configuration / Konfigurace

The project uses a YAML configuration file (`config.yaml`) that is automatically created if not present. You can customize:

```yaml
base_dir: "."
directories:
  pdf: "data/1-pdf"
  markdown_chapters: "data/2-markdown-chapters"
  markdown_chunks: "data/3-markdown-chunks"
  optimized_chunks: "data/4-markdown-chunks-optimized"
  audio_chunks: "data/5-audio-chunks-espeak"
  audio_chapters: "data/6-audio-chapters-espeak"
  paragraphs: "data/7-paragraphs"
tts:
  engine: "espeak-ng"
  voice: "cs"
  rate: 175
  pitch: 50
  volume: 100
chunking:
  max_chunk_size: 5000
processing:
  parallel_jobs: 4
```

## Processing Pipeline / Postup zpracování

```mermaid
graph TD
    A[PDF Files] -->|pdf_extractor.py| B[Markdown Chapters]
    B -->|chunker_splitter.py| C[Markdown Chunks]
    C -->|text_optimizer.py| D[Optimized Markdown Chunks]
    D -->|audio_chunk_generator.py| E[Audio Chunks]
    D -->|espeak_audio_chunk_generator.py| E2[Espeak Audio Chunks]
    E -->|audio_concatenator.py| F[Audio Chapters]
    E2 -->|audio_concatenator.py| F
    F -->|paragraph_separator.py| G[Text Paragraphs]
```

## Directory Structure / Adresářová struktura

- [1-pdf](./data/1-pdf): Source PDF files / Zdrojové PDF soubory
- [2-markdown-chapters](./data/2-markdown-chapters): Extracted markdown chapters / Extrahované markdown kapitoly
- [3-markdown-chunks](./data/3-markdown-chunks): Split markdown files / Rozdělené markdown soubory
- [4-markdown-chunks-optimized](./data/4-markdown-chunks-optimized): Optimized markdown segments / Optimalizované markdown segmenty
- [5-audio-chunks](./data/5-audio-chunks): Audio files generated using ElevenLabs / Zvukové soubory vygenerované pomocí ElevenLabs
- [5-audio-chunks-espeak](./data/5-audio-chunks-espeak): Audio files generated using espeak-ng / Zvukové soubory vygenerované pomocí espeak-ng
- [6-audio-chapters](./data/6-audio-chapters): Concatenated audio files into complete chapters / Spojené zvukové soubory do ucelených kapitol
- [7-paragraphs](./data/7-paragraphs): Separate paragraphs for fine-grained navigation / Samostatné odstavce pro jemnější navigaci

## Modules / Moduly

### 1. PDF Extractor (`pdf_extractor.py`)
Extracts text from PDF files and creates markdown chapter files.
- **Input:** PDF file(s) from `data/1-pdf`
- **Output:** Markdown chapter files in `data/2-markdown-chapters`

### 2. Chunker Splitter (`chunker_splitter.py`)
Splits markdown chapter files into smaller segments for easier processing.
- **Input:** Markdown chapter files from `data/2-markdown-chapters`
- **Output:** Markdown chunks in `data/3-markdown-chunks`
- **Chunk size:** Maximum 5,000 characters per segment

### 3. Text Optimizer (`text_optimizer.py`)
Optimizes markdown chunks for speech synthesis using the Anthropic API.
- **Input:** Markdown chunks from `data/3-markdown-chunks`
- **Output:** Optimized markdown chunks in `data/4-markdown-chunks-optimized`
- **Optimization:** Removes references, footnotes, page numbers; joins hyphenated words at line breaks; fixes formatting

### 4a. Audio Chunk Generator (`audio_chunk_generator.py`)
Converts text files to audio using the ElevenLabs API.
- **Input:** Optimized markdown files from `data/4-markdown-chunks-optimized`
- **Output:** Audio files in `data/5-audio-chunks`
- **Postprocessing:** After processing, input files are marked with the prefix "AUDIO_GENERATED-" to indicate they have been converted to audio

### 4b. Espeak Audio Chunk Generator (`espeak_audio_chunk_generator.py`)
Alternative converter using the open-source espeak-ng TTS engine.
- **Input:** Optimized markdown files from `data/4-markdown-chunks-optimized`
- **Output:** Audio files in `data/5-audio-chunks-espeak`
- **Features:** Free and open-source, works offline, supports Czech language
- **Note:** Lower audio quality than ElevenLabs but useful for prototyping and development

### 5. Audio Concatenator (`audio_concatenator.py`)
Concatenates multiple audio chunks into complete chapter audio files.
- **Input:** Audio chunks from `data/5-audio-chunks` or `data/5-audio-chunks-espeak`
- **Output:** Complete chapter audio files in `data/6-audio-chapters`

### 6. Paragraph Separator (`separate_paragraphs.py`)
Separates text into individual paragraphs for fine-grained navigation.
- **Input:** Optimized markdown chunks from `data/4-markdown-chunks-optimized`
- **Output:** Individual paragraph files in `data/7-paragraphs/text`

## Pipeline Components / Součásti pipeline

### Configuration (`config.py`)
Central configuration system that loads settings from YAML and creates directory structure.

### Processors (`processors.py`)
Adapter classes that provide a consistent interface between pipeline stages.

### Pipeline (`pipeline.py`)
Orchestration system that manages state, tracks progress, and executes processors in sequence.

### CLI (`cli.py`)
Command-line interface for running the pipeline with various options.

## Legacy Batch Processing / Původní hromadné zpracování

To process all remaining files using espeak-ng with the legacy script, run:

```bash
./generate_espeak_audio.sh
```

This will:
1. Process all remaining markdown files that haven't been converted to audio yet
2. Save the generated audio files to `data/5-audio-chunks-espeak`
3. Track progress in `espeak_progress.json`
4. Log detailed information to `espeak_generation.log`

You can customize the processing with these parameters:

```bash
# Process with different voice and rate
./generate_espeak_audio.sh -v cs -r 160 -p 55

# Process only a limited number of files
./generate_espeak_audio.sh --max-files 5

# See all available options
./generate_espeak_audio.sh --help
```

## Text-to-Speech Formatting / Formátování textu pro syntézu řeči

For better control over speech synthesis in ElevenLabs, you can use these special formatting tags:

### Pauses / Pauzy

```
<break time="1s" />     <!-- 1 second pause -->
<break time="500ms" />  <!-- 500 millisecond pause -->
```

### Voice Adjustments / Úpravy hlasu

```
<prosody rate="slow" pitch="+20%">Text with higher pitch and slower rate</prosody>
<emphasis level="strong">Strongly emphasized text</emphasis>
```

### Greek Letters and Variables / Řecká písmena a proměnné

For Greek letters and variables, use plain text pronunciation:

```
"alfa účinku" instead of "α účinku"
"pé jedna větší než pé" instead of "p₁ > p"
```

## FFmpeg Commands for Audio Manipulation / FFmpeg příkazy pro manipulaci s audio

The `audio_concatenator.py` module uses ffmpeg for audio concatenation. Here are some useful ffmpeg commands:

### Concatenating Multiple Audio Files

```bash
# Using a file list
ffmpeg -f concat -safe 0 -i files.txt -c copy output.mp3
```

### Audio Manipulation

```bash
# Trim audio
ffmpeg -i input.mp3 -ss 00:00:10 -to 00:01:00 -c copy output.mp3

# Normalize volume
ffmpeg -i input.mp3 -filter:a loudnorm output.mp3

# Add silence
ffmpeg -i input.mp3 -af "apad=pad_dur=2" output.mp3
```

