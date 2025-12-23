# Human Action Audiobook Generation - Pipeline Execution Summary

## Review Summary / Přehled revize

### ✅ Completed Integrations

#### 1. YouTube Transcription Pipeline
- **Status**: ✅ Integrated into `transcribe/` module
- **Features**: Video download, transcription, multiple output formats
- **Dependencies**: Made optional (Whisper, Vosk, SpeechRecognition)

#### 2. Free TTS/STT Engine Framework
- **TTS Engines**: Piper, Coqui TTS, eSpeak-ng, Mock mode
- **STT Engines**: Whisper, Vosk, SpeechRecognition
- **Auto-Detection**: Priority-based engine selection
- **Status**: Framework complete, engines need installation

#### 3. Dependency Management
- **Anthropic**: Optional (text optimization skipped gracefully)
- **ElevenLabs**: Optional (falls back to free TTS)
- **All Engines**: Graceful degradation when unavailable

### 📊 Current System State

**Python Version**: 3.12.3 (incompatible with Coqui TTS which requires 3.9-3.11)

**Available TTS Engines**: None (all require installation)
- Piper: Binary download needed
- Coqui TTS: Python version incompatible
- eSpeak-ng: System package not installed
- Current: Mock mode (for testing)

**Text Optimization**: Skipped (Anthropic is paid API)

**Files Ready**: 254 unprocessed markdown files

### 🚀 Pipeline Execution Plan

Since no TTS engines are currently installed, we'll:

1. **Skip Optimization Stage** (paid Anthropic API)
2. **Use Mock Mode** to demonstrate pipeline structure
3. **Provide Installation Instructions** for free TTS engines
4. **Execute Available Stages**: PDF extraction, chunking, concatenation

### 📝 Installation Instructions for Free TTS

#### Option 1: Install eSpeak-ng (Recommended - Easiest)
```bash
sudo apt update
sudo apt install espeak-ng
# Then restart the pipeline
python main.py --stage audio-gen
```

#### Option 2: Install Piper TTS (Best Quality)
```bash
# Download binary
wget https://github.com/rhasspy/piper/releases/download/v1.2.0/piper_amd64.tar.gz
tar -xzf piper_amd64.tar.gz
sudo mv piper/piper /usr/local/bin/
sudo mv piper/* /usr/local/share/piper/

# Download Czech voice
mkdir -p ~/.piper/models
cd ~/.piper/models
wget https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/cs/cs_CZ-jirka-medium/cs_CZ-jirka-medium.onnx
wget https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/cs/cs_CZ-jirka-medium/cs_CZ-jirka-medium.onnx.json
```

#### Option 3: Use Existing eSpeak Generator Script
```bash
# Use the existing generate_espeak_audio.py script
python generate_espeak_audio.py
```

### 🎯 Execution Strategy

1. **Skip Optimization**: Use existing optimized files (254 available)
2. **Audio Generation**: Use mock mode to show structure, then install eSpeak-ng for real generation
3. **Concatenation**: Will work once audio files are generated


