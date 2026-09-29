#!/usr/bin/env python3
"""
YouTube Video Transcription Pipeline

Automatizovaný pipeline pro stahování YouTube videí, extrakci audia,
transkripci pomocí OpenAI Whisper a export do více formátů.
"""

import argparse
import asyncio
import json
import logging
import os
import platform
import re
import shutil
import signal
import sys
import time
import uuid
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

import yaml
import yt_dlp

# Try to import STT libraries, make them optional
try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False
    whisper = None

# Try to import alternative STT libraries
try:
    import vosk
    VOSK_AVAILABLE = True
except ImportError:
    VOSK_AVAILABLE = False
    vosk = None

try:
    import speech_recognition as sr
    SPEECH_RECOGNITION_AVAILABLE = True
except ImportError:
    SPEECH_RECOGNITION_AVAILABLE = False
    sr = None

# Determine available STT engines
AVAILABLE_STT_ENGINES = []
if WHISPER_AVAILABLE:
    AVAILABLE_STT_ENGINES.append('whisper')
if VOSK_AVAILABLE:
    AVAILABLE_STT_ENGINES.append('vosk')
if SPEECH_RECOGNITION_AVAILABLE:
    AVAILABLE_STT_ENGINES.append('speech_recognition')

if not AVAILABLE_STT_ENGINES:
    print("WARNING: No STT engines available. Transcription will be unavailable.")
    print("Install STT engines:")
    print("  - pip install openai-whisper (recommended)")
    print("  - pip install vosk (offline)")
    print("  - pip install SpeechRecognition (multiple backends)")

try:
    from googletrans import Translator
except ImportError:
    Translator = None

try:
    import edge_tts
except ImportError:
    edge_tts = None


class TranscriptionPipeline:
    """Hlavní třída pro orchestrace YouTube transcription pipeline."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Inicializace pipeline s konfigurací."""
        self.config = self._load_config(config_path)
        self._setup_logging()
        self._check_ffmpeg()  # Issue #19 - Check FFmpeg early
        self._setup_directories()
        self.current_audio_path = None  # Track current file for cleanup
        
    def _load_config(self, config_path: Optional[str]) -> Dict:
        """Načte konfiguraci z YAML souboru s validací."""
        default_config = {
            'whisper': {
                'model': 'base',
                'device': 'cpu'
            },
            'output': {
                'directory': './output',
                'formats': ['txt', 'srt', 'json', 'vtt']
            },
            'download': {
                'temp_dir': './temp',
                'audio_format': 'mp3',
                'audio_quality': '192'
            },
            'cleanup': {
                'remove_temp_files': True
            },
            'translation': {
                'enabled': False,
                'source_lang': 'en',
                'target_lang': 'cs'
            },
            'tts': {
                'enabled': False,
                'voice': 'cs-CZ-AntoninNeural',
                'rate': '+0%',
                'volume': '+0%'
            },
            'video': {
                'enabled': False,
                'keep_original': True
            }
        }

        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    user_config = yaml.safe_load(f)

                    # Handle None/empty config (Issue #3)
                    if user_config is None:
                        logging.warning(f"Config soubor {config_path} je prázdný, používám výchozí konfiguraci")
                        return default_config

                    # Validate it's a dictionary
                    if not isinstance(user_config, dict):
                        logging.error(f"Config soubor {config_path} neobsahuje platnou konfiguraci")
                        return default_config

                    # Merge user config with defaults (Issue #4 - type checking)
                    for key, value in user_config.items():
                        if key in default_config:
                            # Only merge if both are dicts
                            if isinstance(default_config[key], dict) and isinstance(value, dict):
                                default_config[key].update(value)
                            else:
                                default_config[key] = value
                        else:
                            default_config[key] = value

            except yaml.YAMLError as e:
                # Issue #2 - Handle YAML parse errors
                logging.error(f"Chyba při parsování YAML konfigurace {config_path}: {e}")
                logging.warning("Používám výchozí konfiguraci")
                return default_config
            except Exception as e:
                logging.error(f"Neočekávaná chyba při načítání konfigurace: {e}")
                logging.warning("Používám výchozí konfiguraci")
                return default_config

        # Validate and normalize paths (Issue #5)
        try:
            default_config['output']['directory'] = self._validate_config_path(
                default_config['output']['directory']
            )
            default_config['download']['temp_dir'] = self._validate_config_path(
                default_config['download']['temp_dir']
            )
        except ValueError as e:
            logging.error(f"Neplatná cesta v konfiguraci: {e}")
            # Use safe defaults
            default_config['output']['directory'] = os.path.abspath('./output')
            default_config['download']['temp_dir'] = os.path.abspath('./temp')

        return default_config
    
    def _setup_logging(self):
        """Nastaví logging s podporou pro cleanup."""
        # Issue #15 - Make idempotent
        self.logger = logging.getLogger(__name__)

        # Only setup if no handlers exist
        if not self.logger.handlers:
            self.logger.setLevel(logging.INFO)

            # Console handler
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(
                logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            )
            self.logger.addHandler(console_handler)

            # File handler with proper permissions (Issue #1, #20)
            log_file = 'transcription.log'
            self.file_handler = logging.FileHandler(log_file)
            self.file_handler.setFormatter(
                logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            )
            self.logger.addHandler(self.file_handler)

            # Set file permissions to owner-only (Issue #20)
            try:
                os.chmod(log_file, 0o600)
            except Exception as e:
                self.logger.warning(f"Nelze nastavit oprávnění log souboru: {e}")

    def _cleanup_logging(self):
        """Uzavře logging handlers."""
        if hasattr(self, 'file_handler'):
            self.file_handler.close()
            self.logger.removeHandler(self.file_handler)
    
    def _setup_directories(self):
        """Vytvoří potřebné adresáře."""
        try:
            os.makedirs(self.config['output']['directory'], exist_ok=True)
            os.makedirs(self.config['download']['temp_dir'], exist_ok=True)
        except OSError as e:
            self.logger.error(f"Nelze vytvořit adresář: {e}")
            raise

    def _check_ffmpeg(self) -> bool:
        """Zkontroluje dostupnost FFmpeg, poskytne návod k instalaci pokud chybí."""
        if shutil.which('ffmpeg'):
            return True

        system = platform.system()
        if system == "Linux":
            distro_check = ""
            if os.path.exists('/etc/os-release'):
                with open('/etc/os-release', 'r') as f:
                    os_info = f.read().lower()
                    if 'ubuntu' in os_info or 'debian' in os_info:
                        distro_check = "sudo apt update && sudo apt install ffmpeg"
                    elif 'fedora' in os_info or 'rhel' in os_info or 'centos' in os_info:
                        distro_check = "sudo dnf install ffmpeg"
                    else:
                        distro_check = "sudo apt install ffmpeg  # nebo sudo dnf install ffmpeg"
            install_cmd = distro_check if distro_check else "sudo apt install ffmpeg"
        elif system == "Darwin":
            install_cmd = "brew install ffmpeg"
        elif system == "Windows":
            install_cmd = "Stáhněte z https://ffmpeg.org/download.html a přidejte do PATH"
        else:
            install_cmd = "Viz https://ffmpeg.org/download.html"

        error_msg = f"""
FFmpeg není nainstalován!

FFmpeg je vyžadován pro extrakci audia z videí.

Instalace pro {system}:
{install_cmd}

Po instalaci restartujte příkaz.
"""
        self.logger.error(error_msg)
        raise RuntimeError(error_msg)

    def _validate_config_path(self, path: str) -> str:
        """Validuje a normalizuje cestu z konfigurace pro bezpečnost."""
        if not path:
            raise ValueError("Cesta nemůže být prázdná")

        # Normalizuj cestu
        normalized = os.path.normpath(path)

        # Pokud je relativní, udělej ji absolutní vůči CWD
        if not os.path.isabs(normalized):
            normalized = os.path.abspath(normalized)

        return normalized

    def _check_cuda_available(self) -> str:
        """Zkontroluje dostupnost CUDA, fallback na CPU pokud není k dispozici."""
        device = self.config['whisper']['device']

        if device == 'cuda':
            try:
                import torch
                if torch.cuda.is_available():
                    self.logger.info("CUDA je dostupná, používám GPU")
                    return 'cuda'
                else:
                    self.logger.warning("CUDA není dostupná, přepínám na CPU")
                    return 'cpu'
            except ImportError:
                self.logger.warning("PyTorch není nainstalován nebo CUDA není dostupná, používám CPU")
                return 'cpu'

        return device

    def _ensure_unique_filename(self, base_filename: str) -> str:
        """Zajistí unikátní název souboru, v případě kolize se zeptá uživatele."""
        output_dir = os.path.join(self.config['output']['directory'], base_filename)

        if not os.path.exists(output_dir):
            return base_filename

        # Adresář už existuje - zeptáme se uživatele
        print(f"\n⚠️  Adresář '{base_filename}' již existuje.")
        response = input("Přepsat existující transkripci? [y/N]: ")

        if response.lower() == 'y':
            self.logger.info(f"Přepisuju existující transkripci: {base_filename}")
            return base_filename
        else:
            # Vytvoř unikátní název s časovým razítkem
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            new_filename = f"{base_filename}_{timestamp}"
            self.logger.info(f"Vytvářím novou transkripci: {new_filename}")
            return new_filename

    def _validate_url(self, url: str) -> bool:
        """Validuje URL - podporuje YouTube a přímé video URL."""
        # Issue #14 - Add regex anchors for precise matching
        # YouTube patterns
        youtube_patterns = [
            r'^(?:https?://)?(?:www\.)?youtube\.com/watch\?v=[\w-]+(?:&.*)?$',
            r'^(?:https?://)?(?:www\.)?youtu\.be/[\w-]+(?:\?.*)?$',
            r'^(?:https?://)?(?:www\.)?youtube\.com/embed/[\w-]+(?:\?.*)?$'
        ]

        # Direct video URL patterns (common video extensions and CDN URLs)
        video_patterns = [
            r'^(?:https?://).*\.(?:mp4|avi|mkv|mov|wmv|flv|webm|m4v|3gp)(?:\?.*)?$',
            r'^(?:https?://).*\.(?:mp3|wav|aac|ogg|flac|m4a)(?:\?.*)?$'
        ]

        # Check YouTube patterns
        for pattern in youtube_patterns:
            if re.match(pattern, url):
                return True

        # Check video file patterns
        for pattern in video_patterns:
            if re.match(pattern, url, re.IGNORECASE):
                return True

        # Allow any HTTP/HTTPS URL as fallback (yt-dlp will handle validation)
        if url.startswith(('http://', 'https://')):
            return True

        return False
    
    def _get_video_info(self, url: str) -> Dict:
        """Získá informace o videu bez stažení."""
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(url, download=False)
                return {
                    'title': info.get('title', 'Unknown'),
                    'duration': info.get('duration', 0),
                    'uploader': info.get('uploader', 'Unknown')
                }
            except Exception as e:
                self.logger.error(f"Chyba při získávání informací o videu: {e}")
                raise
    
    def _sanitize_filename(self, filename: str) -> str:
        """Vyčistí název souboru od neplatných znaků."""
        # Odstraní neplatné znaky pro soubory
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        filename = filename.strip()

        # Issue #21 - Better truncation to avoid collisions
        max_length = 100
        if len(filename) > max_length:
            # Split into base and extension if any
            parts = filename.rsplit('.', 1)
            if len(parts) == 2 and len(parts[1]) < 10:  # Has extension
                base, ext = parts
                # Keep room for extension + separator
                available = max_length - len(ext) - 1
                filename = base[:available] + '.' + ext
            else:
                # No extension or extension too long, just truncate
                filename = filename[:max_length]

        return filename
    
    def download_audio(self, url: str) -> str:
        """Stáhne audio z YouTube videa."""
        if not self._validate_url(url):
            raise ValueError(f"Neplatná YouTube URL: {url}")

        self.logger.info(f"Stahuji audio z: {url}")

        # Získáme informace o videu
        video_info = self._get_video_info(url)
        safe_title = self._sanitize_filename(video_info['title'])

        # Issue #22 - Add unique ID to prevent concurrent execution conflicts
        unique_id = str(uuid.uuid4())[:8]
        temp_filename = f'{safe_title}_{unique_id}'

        # Nastavení pro yt-dlp
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(
                self.config['download']['temp_dir'],
                f'{temp_filename}.%(ext)s'
            ),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': self.config['download']['audio_format'],
                'preferredquality': self.config['download']['audio_quality'],
            }],
            'quiet': True,
            'no_warnings': True,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            # Najdeme stažený soubor
            audio_path = os.path.join(
                self.config['download']['temp_dir'],
                f'{temp_filename}.{self.config["download"]["audio_format"]}'
            )

            # Issue #8 - Validate file exists
            if not os.path.exists(audio_path):
                raise FileNotFoundError(f"Audio soubor nebyl nalezen: {audio_path}")

            self.logger.info(f"Audio úspěšně stáženo: {audio_path}")
            return audio_path

        except yt_dlp.utils.DownloadError as e:
            # Issue #6 - Better exception handling
            self.logger.error(f"Chyba při stahování videa: {e}")
            self.logger.error("Zkontrolujte URL nebo připojení k internetu")
            raise
        except Exception as e:
            self.logger.error(f"Neočekávaná chyba při stahování audia: {e}")
            raise
    
    def transcribe(self, audio_path: str) -> Dict:
        """Transcribuje audio pomocí dostupného STT engine."""
        # Issue #8 - Validate audio file exists
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio soubor neexistuje: {audio_path}")

        # Check if any STT engine is available
        if not AVAILABLE_STT_ENGINES:
            error_msg = (
                "Žádný STT engine není k dispozici!\n"
                "Nainstalujte alespoň jeden STT engine:\n"
                "  - pip install openai-whisper (doporučeno)\n"
                "  - pip install vosk (offline)\n"
                "  - pip install SpeechRecognition (více backendů)"
            )
            self.logger.error(error_msg)
            raise ImportError("No STT engines available - transcription disabled")

        # Determine which STT engine to use (priority: whisper > vosk > speech_recognition)
        stt_engine = self.config.get('stt', {}).get('engine', 'whisper')
        if stt_engine not in AVAILABLE_STT_ENGINES:
            # Fallback to first available engine
            stt_engine = AVAILABLE_STT_ENGINES[0]
            self.logger.warning(f"Requested STT engine '{self.config.get('stt', {}).get('engine', 'whisper')}' not available, using '{stt_engine}'")

        self.logger.info(f"Používám STT engine: {stt_engine}")
        self.logger.info(f"Transkribuji audio: {audio_path}")

        try:
            if stt_engine == 'whisper':
                result = self._transcribe_with_whisper(audio_path)
            elif stt_engine == 'vosk':
                result = self._transcribe_with_vosk(audio_path)
            elif stt_engine == 'speech_recognition':
                result = self._transcribe_with_speech_recognition(audio_path)
            else:
                raise ValueError(f"Nepodporovaný STT engine: {stt_engine}")

            self.logger.info("Transkripce dokončena")
            return result

        except Exception as e:
            self.logger.error(f"Chyba při transkripci: {e}")
            raise

    def _transcribe_with_whisper(self, audio_path: str) -> Dict:
        """Transcribe using OpenAI Whisper."""
        # Issue #16 - Check CUDA availability and fallback
        device = self._check_cuda_available()

        # Issue #9 - Better model loading error handling
        model_name = self.config['whisper']['model']
        self.logger.info(f"Načítám Whisper model: {model_name} na zařízení: {device}")

        try:
            model = whisper.load_model(model_name, device=device)
        except FileNotFoundError:
            self.logger.error(f"Model '{model_name}' nebyl nalezen. Platné modely: tiny, base, small, medium, large")
            raise
        except RuntimeError as e:
            if "out of memory" in str(e).lower():
                self.logger.error(f"Nedostatek paměti pro model '{model_name}'. Zkuste menší model (tiny, base, small)")
            raise

        # Transcribe audio
        result = model.transcribe(audio_path)
        return result

    def _transcribe_with_vosk(self, audio_path: str) -> Dict:
        """Transcribe using Vosk (offline speech recognition)."""
        self.logger.warning("Vosk STT zatím není implementován - použijte Whisper")
        raise NotImplementedError("Vosk transcription not yet implemented")

    def _transcribe_with_speech_recognition(self, audio_path: str) -> Dict:
        """Transcribe using SpeechRecognition library."""
        self.logger.warning("SpeechRecognition STT zatím není implementován - použijte Whisper")
        raise NotImplementedError("SpeechRecognition transcription not yet implemented")

    def _translate_text(self, transcript: Dict) -> Dict:
        """Přeloží transkript do cílového jazyka pomocí Google Translate."""
        if not self.config['translation']['enabled']:
            return transcript

        if Translator is None:
            self.logger.warning("googletrans není nainstalován, překlad přeskočen")
            return transcript

        target_lang = self.config['translation']['target_lang']
        source_lang = self.config['translation']['source_lang']
        self.logger.info(f"Překládám z {source_lang} do {target_lang}")

        async def translate_segments() -> Dict:
            translated_transcript = transcript.copy()
            translated_transcript['text'] = ""
            translated_segments = []

            async with Translator() as translator:
                for segment in transcript.get('segments', []):
                    original_text = segment.get('text', '').strip()
                    if not original_text:
                        continue

                    result = await translator.translate(
                        original_text,
                        src=source_lang,
                        dest=target_lang,
                    )
                    translated_text = result.text

                    translated_segment = segment.copy()
                    translated_segment['text'] = translated_text
                    translated_segments.append(translated_segment)
                    translated_transcript['text'] += translated_text + " "

            translated_transcript['text'] = translated_transcript['text'].strip()
            translated_transcript['segments'] = translated_segments
            translated_transcript['language'] = target_lang
            return translated_transcript

        try:
            translated = asyncio.run(translate_segments())
            self.logger.info("Překlad dokončen")
            return translated
        except Exception as e:
            self.logger.error(f"Chyba při překladu: {e}")
            return transcript

    def _generate_tts_audio(self, transcript: Dict, output_path: str) -> str:
        """Vygeneruje TTS audio z transkriptu s původním časováním."""
        if not self.config['tts']['enabled']:
            return ""

        if edge_tts is None:
            self.logger.warning("edge-tts není nainstalován, TTS přeskočen")
            return ""

        self.logger.info(f"Generuji TTS audio: {output_path}")

        try:
            # Vytvoříme seznam segmentů s textem a časováním
            segments = []
            for segment in transcript.get('segments', []):
                if segment['text'].strip():
                    segments.append({
                        'text': segment['text'].strip(),
                        'start': segment['start'],
                        'end': segment['end']
                    })

            if not segments:
                self.logger.warning("Žádné segmenty k TTS generování")
                return ""

            # Vytvoříme dočasný adresář pro segmenty
            temp_dir = os.path.join(self.config['download']['temp_dir'], 'tts_segments')
            os.makedirs(temp_dir, exist_ok=True)

            # Nastavíme parametry TTS
            voice = self.config['tts']['voice']
            rate = self.config['tts']['rate']
            volume = self.config['tts']['volume']

            async def generate_segment_audio(segment, idx):
                """Asynchronně vygeneruje audio pro jeden segment."""
                segment_path = os.path.join(temp_dir, f'segment_{idx:04d}.mp3')

                try:
                    communicate = edge_tts.Communicate(segment['text'], voice, rate=rate, volume=volume)
                    await communicate.save(segment_path)
                    return segment_path, segment['start'], segment['end']
                except Exception as e:
                    self.logger.error(f"Chyba při generování segmentu {idx}: {e}")
                    return None, segment['start'], segment['end']

            # Spustíme asynchronní generování všech segmentů
            async def generate_all_segments():
                tasks = [generate_segment_audio(segment, idx) for idx, segment in enumerate(segments)]
                return await asyncio.gather(*tasks)

            # Spustíme event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            results = loop.run_until_complete(generate_all_segments())
            loop.close()

            # Zpracujeme výsledky
            segment_files = []
            max_end_time = 0

            for result in results:
                if result[0] is not None:  # Úspěšně vygenerovaný segment
                    segment_files.append(result)
                    max_end_time = max(max_end_time, result[2])

            if not segment_files:
                self.logger.error("Žádný TTS segment nebyl úspěšně vygenerován")
                return ""

            # Spojíme segmenty do finálního audio souboru pomocí ffmpeg
            self._combine_tts_segments(segment_files, output_path, max_end_time)

            # Vyčistíme dočasné soubory
            shutil.rmtree(temp_dir, ignore_errors=True)

            self.logger.info(f"TTS audio vygenerováno: {output_path}")
            return output_path

        except Exception as e:
            self.logger.error(f"Chyba při generování TTS: {e}")
            return ""

    def _combine_tts_segments(self, segment_files: List[Tuple[str, float, float]], output_path: str, max_duration: float):
        """Spojí TTS segmenty do finálního audio souboru s časováním."""
        try:
            import ffmpeg

            # Vytvoříme seznam vstupů pro ffmpeg
            inputs = []
            filter_complex = []

            for i, (segment_path, start_time, end_time) in enumerate(segment_files):
                inputs.append(ffmpeg.input(segment_path))

                # Přidáme delay pro správné časování
                if start_time > 0:
                    delay_ms = int(start_time * 1000)
                    filter_complex.append(f"[{i}:a]adelay={delay_ms}|{delay_ms}[a{i}];")
                else:
                    filter_complex.append(f"[{i}:a][a{i}];")

            # Spojíme všechny audio stopy
            if len(segment_files) > 1:
                # Pro více segmentů použijeme amix
                amix_inputs = "".join([f"[a{i}]" for i in range(len(segment_files))])
                filter_complex.append(f"{amix_inputs}amix=inputs={len(segment_files)}:duration=longest[aout]")

                # Aplikujeme filter
                filter_str = "".join(filter_complex)
                stream = ffmpeg.filter(inputs, filter_complex[:-1])  # Odstraníme poslední ;
            else:
                # Pro jeden segment žádný filter nepotřebujeme
                stream = inputs[0]

            # Exportujeme finální audio
            stream = ffmpeg.output(stream, output_path, acodec='mp3', audio_bitrate='192k')
            ffmpeg.run(stream, quiet=True, overwrite_output=True)

        except ImportError:
            self.logger.warning("ffmpeg-python není nainstalován, používám jednoduché spojení")
            # Fallback: prostě spojíme soubory bez časování
            with open(output_path, 'wb') as outfile:
                for segment_path, _, _ in segment_files:
                    with open(segment_path, 'rb') as infile:
                        outfile.write(infile.read())
        except Exception as e:
            self.logger.error(f"Chyba při kombinování TTS segmentů: {e}")
            raise

    def _combine_audio_video(self, video_url: str, audio_path: str, output_path: str) -> str:
        """Spojí audio s videem pomocí ffmpeg."""
        if not self.config['video']['enabled']:
            return ""

        self.logger.info(f"Kombinuji audio s videem: {output_path}")

        try:
            import ffmpeg

            # Stáhneme video bez audia
            temp_video_path = os.path.join(self.config['download']['temp_dir'], 'temp_video.mp4')

            # Nastavení pro yt-dlp - stáhnout jen video bez audia
            ydl_opts = {
                'format': 'bestvideo[ext=mp4]/best[ext=mp4]',
                'outtmpl': temp_video_path,
                'quiet': True,
                'no_warnings': True,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([video_url])

            # Zkontrolujeme, že video bylo staženo
            if not os.path.exists(temp_video_path):
                raise FileNotFoundError(f"Video soubor nebyl nalezen: {temp_video_path}")

            # Spojíme video s novým audiem pomocí ffmpeg
            video_stream = ffmpeg.input(temp_video_path)
            audio_stream = ffmpeg.input(audio_path)

            # Kombinujeme video a audio
            stream = ffmpeg.output(
                video_stream,
                audio_stream,
                output_path,
                vcodec='copy',  # Zachováme původní video kodek
                acodec='aac',   # Překódujeme audio na AAC
                audio_bitrate='192k',
                **{'avoid_negative_ts': 'make_zero'}  # Vyhneme se problémům s časováním
            )

            # Spustíme ffmpeg
            ffmpeg.run(stream, quiet=True, overwrite_output=True)

            # Vyčistíme dočasné video
            if os.path.exists(temp_video_path):
                os.remove(temp_video_path)

            self.logger.info(f"Video s novým audiem vytvořeno: {output_path}")
            return output_path

        except ImportError:
            self.logger.warning("ffmpeg-python není nainstalován, video rekombinace přeskočena")
            return ""
        except Exception as e:
            self.logger.error(f"Chyba při kombinování audio a videa: {e}")
            # Vyčistíme dočasné soubory v případě chyby
            temp_video_path = os.path.join(self.config['download']['temp_dir'], 'temp_video.mp4')
            if os.path.exists(temp_video_path):
                os.remove(temp_video_path)
            return ""
    
    def _format_time_srt(self, seconds: float) -> str:
        """Formátuje čas pro SRT formát s přesným výpočtem."""
        # Issue #27 - Use Decimal for precision
        dec_seconds = Decimal(str(seconds))
        hours = int(dec_seconds // 3600)
        minutes = int((dec_seconds % 3600) // 60)
        secs = int(dec_seconds % 60)
        milliseconds = int((dec_seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"

    def _format_time_vtt(self, seconds: float) -> str:
        """Formátuje čas pro VTT formát s přesným výpočtem."""
        # Issue #27 - Use Decimal for precision
        dec_seconds = Decimal(str(seconds))
        hours = int(dec_seconds // 3600)
        minutes = int((dec_seconds % 3600) // 60)
        secs = float(dec_seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"
    
    def export_txt(self, transcript: Dict, output_path: str):
        """Exportuje transkript jako plain text."""
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(transcript['text'])
        self.logger.info(f"TXT export dokončen: {output_path}")
    
    def export_srt(self, transcript: Dict, output_path: str):
        """Exportuje transkript jako SRT formát s validací."""
        with open(output_path, 'w', encoding='utf-8') as f:
            segment_num = 1
            # Issue #10 - Validate segments exist
            for segment in transcript.get('segments', []):
                # Issue #10 - Validate required keys
                if not all(k in segment for k in ['start', 'end', 'text']):
                    self.logger.warning(f"Přeskakuji neplatný segment: {segment}")
                    continue

                text = segment['text'].strip()

                # Issue #11 - Filter empty segments
                if not text:
                    continue

                start_time = self._format_time_srt(segment['start'])
                end_time = self._format_time_srt(segment['end'])

                f.write(f"{segment_num}\n")
                f.write(f"{start_time} --> {end_time}\n")
                f.write(f"{text}\n\n")
                segment_num += 1

        self.logger.info(f"SRT export dokončen: {output_path}")
    
    def export_json(self, transcript: Dict, output_path: str):
        """Exportuje transkript jako JSON s metadata."""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(transcript, f, ensure_ascii=False, indent=2)
        self.logger.info(f"JSON export dokončen: {output_path}")
    
    def export_vtt(self, transcript: Dict, output_path: str):
        """Exportuje transkript jako WebVTT formát s validací."""
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("WEBVTT\n\n")

            # Issue #10 - Validate segments exist
            for segment in transcript.get('segments', []):
                # Issue #10 - Validate required keys
                if not all(k in segment for k in ['start', 'end', 'text']):
                    self.logger.warning(f"Přeskakuji neplatný segment: {segment}")
                    continue

                text = segment['text'].strip()

                # Issue #11 - Filter empty segments
                if not text:
                    continue

                start_time = self._format_time_vtt(segment['start'])
                end_time = self._format_time_vtt(segment['end'])

                f.write(f"{start_time} --> {end_time}\n")
                f.write(f"{text}\n\n")

        self.logger.info(f"VTT export dokončen: {output_path}")
    
    def export_transcripts(self, transcript: Dict, base_filename: str, formats: List[str]):
        """Exportuje transkripty do specifikovaných formátů s validací."""
        # Issue #26 - Directory structure: Each video gets its own subdirectory
        # This keeps related files together and prevents filename collisions
        output_dir = os.path.join(self.config['output']['directory'], base_filename)

        # Issue #13, #23 - Better directory creation error handling
        try:
            os.makedirs(output_dir, exist_ok=True)
        except OSError as e:
            self.logger.error(f"Nelze vytvořit výstupní adresář {output_dir}: {e}")
            raise

        exporters = {
            'txt': self.export_txt,
            'srt': self.export_srt,
            'json': self.export_json,
            'vtt': self.export_vtt
        }

        # Issue #24 - Validate format names
        valid_formats = set(exporters.keys())
        invalid_formats = [f for f in formats if f not in valid_formats]
        if invalid_formats:
            self.logger.warning(
                f"Nepodporované formáty (přeskakuji): {', '.join(invalid_formats)}. "
                f"Platné formáty: {', '.join(valid_formats)}"
            )

        for format_type in formats:
            if format_type in exporters:
                output_path = os.path.join(output_dir, f"{base_filename}.{format_type}")
                try:
                    exporters[format_type](transcript, output_path)
                except Exception as e:
                    self.logger.error(f"Chyba při exportu {format_type}: {e}")
                    # Continue with other formats even if one fails
                    continue
    
    def cleanup(self, audio_path: str):
        """Vyčistí dočasné soubory."""
        if self.config['cleanup']['remove_temp_files'] and os.path.exists(audio_path):
            os.remove(audio_path)
            self.logger.info(f"Dočasný soubor odstraněn: {audio_path}")
    
    def run(self, url: str, formats: Optional[List[str]] = None) -> str:
        """Spustí kompletní pipeline s robustním error handlingem."""
        if formats is None:
            formats = self.config['output']['formats']

        audio_path = None

        try:
            # Issue #18 - Cache video_info to avoid duplicate API calls
            video_info = self._get_video_info(url)
            base_filename = self._sanitize_filename(video_info['title'])

            # Issue #17 - Handle filename collisions with user prompts
            base_filename = self._ensure_unique_filename(base_filename)

            # Stáhne audio
            audio_path = self.download_audio(url)
            self.current_audio_path = audio_path  # Track for signal handler

            # Transkribuje
            transcript = self.transcribe(audio_path)

            # Přeloží transkript pokud je povoleno
            if self.config['translation']['enabled']:
                translated_transcript = self._translate_text(transcript)
                # Exportuje původní transkripty
                self.export_transcripts(transcript, base_filename, formats)
                # Exportuje přeložené transkripty s "_cs" suffix
                translated_filename = f"{base_filename}_cs"
                self.export_transcripts(translated_transcript, translated_filename, formats)
                # Použijeme přeložený transkript pro další kroky
                working_transcript = translated_transcript
            else:
                # Exportuje původní transkripty
                self.export_transcripts(transcript, base_filename, formats)
                working_transcript = transcript

            # Vygeneruje TTS audio pokud je povoleno
            tts_audio_path = ""
            if self.config['tts']['enabled']:
                tts_filename = f"{base_filename}_tts.mp3"
                tts_output_dir = os.path.join(self.config['output']['directory'], base_filename)
                os.makedirs(tts_output_dir, exist_ok=True)
                tts_audio_path = os.path.join(tts_output_dir, tts_filename)
                tts_audio_path = self._generate_tts_audio(working_transcript, tts_audio_path)

            # Rekombinuje video s novým audiem pokud je povoleno
            video_path = ""
            if self.config['video']['enabled'] and tts_audio_path:
                video_filename = f"{base_filename}_cs.mp4"
                video_output_dir = os.path.join(self.config['output']['directory'], base_filename)
                os.makedirs(video_output_dir, exist_ok=True)
                video_path = os.path.join(video_output_dir, video_filename)
                video_path = self._combine_audio_video(url, tts_audio_path, video_path)

            output_dir = os.path.join(self.config['output']['directory'], base_filename)
            self.logger.info(f"Pipeline dokončen. Výstup: {output_dir}")
            return output_dir

        except KeyboardInterrupt:
            # Issue #25 - Handle Ctrl+C gracefully
            self.logger.warning("\nOperace přerušena uživatelem")
            raise

        except Exception as e:
            self.logger.error(f"Chyba v pipeline: {e}")
            raise

        finally:
            # Issue #12 - Always cleanup temp files
            if audio_path and self.config['cleanup']['remove_temp_files']:
                self.cleanup(audio_path)
            self.current_audio_path = None


def main():
    """Hlavní funkce pro CLI s signal handlingem."""
    parser = argparse.ArgumentParser(
        description='YouTube Video Transcription Pipeline',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Příklady použití:
  python transcribe.py "https://www.youtube.com/watch?v=VIDEO_ID"
  python transcribe.py "URL" --config my-config.yaml --model medium
  python transcribe.py "URL" --formats txt,srt --output ./my-transcripts
  python transcribe.py "URL" --translate --tts --video
  python transcribe.py "URL" --translate --target-lang cs --tts-voice cs-CZ-AntoninNeural
        """
    )

    parser.add_argument('url', help='YouTube URL k transkripci')
    parser.add_argument('--config', '-c', help='Cesta k YAML konfiguračnímu souboru')
    parser.add_argument('--output', '-o', help='Výstupní adresář')
    parser.add_argument('--model', '-m',
                       choices=['tiny', 'base', 'small', 'medium', 'large'],
                       help='Whisper model velikost')
    parser.add_argument('--formats', '-f',
                       help='Formáty výstupu oddělené čárkou (txt,srt,json,vtt)')
    parser.add_argument('--device', '-d',
                       choices=['cpu', 'cuda'],
                       help='Zařízení pro Whisper (cpu/cuda)')

    # Nové možnosti pro překlad, TTS a video
    parser.add_argument('--translate', action='store_true',
                       help='Přeložit transkript do češtiny')
    parser.add_argument('--tts', action='store_true',
                       help='Vygenerovat české TTS audio')
    parser.add_argument('--video', action='store_true',
                       help='Vytvořit video s českým audiem')
    parser.add_argument('--source-lang', default='en',
                       help='Zdrojový jazyk pro překlad, výchozí: en')
    parser.add_argument('--target-lang', default='cs',
                       help='Cílový jazyk pro překlad, výchozí: cs')
    parser.add_argument('--tts-voice', default='cs-CZ-AntoninNeural',
                       help='Hlas pro TTS, výchozí: cs-CZ-AntoninNeural')
    parser.add_argument('--tts-rate', default='+0%',
                       help='Rychlost TTS, výchozí: +0%%')
    parser.add_argument('--tts-volume', default='+0%',
                       help='Hlasitost TTS, výchozí: +0%%')

    args = parser.parse_args()

    pipeline = None

    def signal_handler(signum, frame):
        """Issue #25 - Handle Ctrl+C gracefully."""
        print("\n\nPřerušení detekováno...")
        if pipeline and pipeline.current_audio_path:
            print("Čistím dočasné soubory...")
            pipeline.cleanup(pipeline.current_audio_path)
        if pipeline:
            pipeline._cleanup_logging()
        sys.exit(1)

    # Register signal handler
    signal.signal(signal.SIGINT, signal_handler)

    try:
        # Vytvoří pipeline
        pipeline = TranscriptionPipeline(args.config)

        # Override konfigurace z CLI argumentů
        if args.output:
            pipeline.config['output']['directory'] = args.output
        if args.model:
            pipeline.config['whisper']['model'] = args.model
        if args.device:
            pipeline.config['whisper']['device'] = args.device
        if args.formats:
            # Issue #24 - Validate format names
            formats = [f.strip() for f in args.formats.split(',')]
            valid_formats = {'txt', 'srt', 'json', 'vtt'}
            invalid = set(formats) - valid_formats
            if invalid:
                print(f"Varování: Neplatné formáty (ignoruji): {', '.join(invalid)}")
                print(f"Platné formáty: {', '.join(valid_formats)}")
            pipeline.config['output']['formats'] = [f for f in formats if f in valid_formats]

        # Override konfigurace pro nové funkce
        if args.translate:
            pipeline.config['translation']['enabled'] = True
        if args.source_lang:
            pipeline.config['translation']['source_lang'] = args.source_lang
        if args.target_lang:
            pipeline.config['translation']['target_lang'] = args.target_lang
        if args.tts:
            pipeline.config['tts']['enabled'] = True
        if args.tts_voice:
            pipeline.config['tts']['voice'] = args.tts_voice
        if args.tts_rate:
            pipeline.config['tts']['rate'] = args.tts_rate
        if args.tts_volume:
            pipeline.config['tts']['volume'] = args.tts_volume
        if args.video:
            pipeline.config['video']['enabled'] = True

        # Spustí pipeline
        output_dir = pipeline.run(args.url)
        print(f"\n✅ Transkripce dokončena. Výstup: {output_dir}")

        # Cleanup logging
        pipeline._cleanup_logging()
        sys.exit(0)

    except KeyboardInterrupt:
        print("\n\nOperace přerušena uživatelem.")
        if pipeline:
            pipeline._cleanup_logging()
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Chyba: {e}")
        if pipeline:
            pipeline._cleanup_logging()
        sys.exit(1)


if __name__ == "__main__":
    main()

