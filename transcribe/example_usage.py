#!/usr/bin/env python3
"""
Příklad použití YouTube Transcription Pipeline

Tento skript ukazuje, jak používat pipeline programově.
"""

import os
import sys
from pathlib import Path

# Přidáme aktuální adresář do Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from transcribe import TranscriptionPipeline


def example_basic_usage():
    """Základní příklad použití."""
    print("📝 Příklad 1: Základní použití")
    
    # Vytvoření pipeline s default konfigurací
    pipeline = TranscriptionPipeline()
    
    # URL YouTube videa (použijte skutečné URL)
    youtube_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    
    try:
        # Spuštění pipeline
        output_dir = pipeline.run(youtube_url)
        print(f"✅ Transkripce dokončena. Výstup: {output_dir}")
        
    except Exception as e:
        print(f"❌ Chyba: {e}")


def example_custom_config():
    """Příklad s custom konfigurací."""
    print("\n📝 Příklad 2: Custom konfigurace")
    
    # Vytvoření custom konfigurace
    custom_config = {
        'whisper': {
            'model': 'small',  # Rychlejší než base
            'device': 'cpu'
        },
        'output': {
            'directory': './my_transcripts',
            'formats': ['txt', 'srt']  # Pouze TXT a SRT
        },
        'download': {
            'temp_dir': './temp',
            'audio_format': 'mp3',
            'audio_quality': '128'  # Nižší kvalita = rychlejší
        }
    }
    
    # Uložení custom konfigurace
    import yaml
    with open('custom_config.yaml', 'w') as f:
        yaml.dump(custom_config, f)
    
    # Vytvoření pipeline s custom konfigurací
    pipeline = TranscriptionPipeline('custom_config.yaml')
    
    youtube_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    
    try:
        output_dir = pipeline.run(youtube_url)
        print(f"✅ Transkripce s custom konfigurací dokončena: {output_dir}")
        
    except Exception as e:
        print(f"❌ Chyba: {e}")
    
    # Vyčištění
    if os.path.exists('custom_config.yaml'):
        os.remove('custom_config.yaml')


def example_batch_processing():
    """Příklad batch zpracování více videí."""
    print("\n📝 Příklad 3: Batch zpracování")
    
    # Seznam YouTube URL
    urls = [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://www.youtube.com/watch?v=VIDEO_ID_2",
        "https://www.youtube.com/watch?v=VIDEO_ID_3"
    ]
    
    pipeline = TranscriptionPipeline()
    
    for i, url in enumerate(urls, 1):
        print(f"🎥 Zpracovávám video {i}/{len(urls)}: {url}")
        
        try:
            output_dir = pipeline.run(url, formats=['txt', 'json'])
            print(f"✅ Video {i} dokončeno: {output_dir}")
            
        except Exception as e:
            print(f"❌ Chyba u videa {i}: {e}")


def example_programmatic_usage():
    """Příklad programového použití jednotlivých komponent."""
    print("\n📝 Příklad 4: Programové použití komponent")
    
    pipeline = TranscriptionPipeline()
    
    youtube_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    
    try:
        # Krok 1: Stažení audia
        print("📥 Stahuji audio...")
        audio_path = pipeline.download_audio(youtube_url)
        print(f"✅ Audio staženo: {audio_path}")
        
        # Krok 2: Transkripce
        print("🗣️ Transkribuji...")
        transcript = pipeline.transcribe(audio_path)
        print(f"✅ Transkripce dokončena. Jazyk: {transcript.get('language', 'neznámý')}")
        
        # Krok 3: Export do různých formátů
        print("📄 Exportuji...")
        video_info = pipeline._get_video_info(youtube_url)
        base_filename = pipeline._sanitize_filename(video_info['title'])
        
        # Export do všech formátů
        pipeline.export_transcripts(transcript, base_filename, ['txt', 'srt', 'json', 'vtt'])
        print("✅ Export dokončen")
        
        # Krok 4: Vyčištění
        pipeline.cleanup(audio_path)
        print("🧹 Dočasné soubory vyčištěny")
        
    except Exception as e:
        print(f"❌ Chyba: {e}")


def main():
    """Hlavní funkce s příklady."""
    print("🎬 YouTube Transcription Pipeline - Příklady použití\n")
    
    print("⚠️  POZOR: Tyto příklady používají testovací URL.")
    print("   Pro skutečné použití nahraďte URL skutečnými YouTube videi.\n")
    
    # Spuštění příkladů
    example_basic_usage()
    example_custom_config()
    example_batch_processing()
    example_programmatic_usage()
    
    print("\n🎉 Všechny příklady dokončeny!")
    print("\n📚 Pro více informací viz README.md")


if __name__ == "__main__":
    main()

