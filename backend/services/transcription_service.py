# backend/services/transcription_service.py
import os
import time
import json
import tempfile
import logging
import subprocess
from pathlib import Path
import wave

from config import logger

# Try to load faster-whisper first (preferred for speed)
try:
    from faster_whisper import WhisperModel
    FASTER_WHISPER_AVAILABLE = True
    
    # Load the model (use "tiny" or "base" for fastest results)
    # Options: "tiny", "base", "small", "medium", "large-v1", "large-v2", "large-v3"
    MODEL_SIZE = "base"
    # Use device="cuda" and compute_type="float16" if you have a GPU
    whisper_model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")
    logger.info(f"Faster Whisper model '{MODEL_SIZE}' loaded successfully")
except ImportError:
    FASTER_WHISPER_AVAILABLE = False
    logger.warning("faster-whisper library not available. Consider installing it for faster transcription.")

# Try regular whisper as fallback
if not FASTER_WHISPER_AVAILABLE:
    try:
        import whisper
        WHISPER_AVAILABLE = True
        # Load the model (smaller = faster)
        # Options: "tiny", "base", "small", "medium", "large"
        MODEL_SIZE = "base"
        whisper_model = whisper.load_model(MODEL_SIZE)
        logger.info(f"Regular Whisper model '{MODEL_SIZE}' loaded successfully")
    except ImportError:
        WHISPER_AVAILABLE = False
        logger.warning("Whisper library not available. Please install it with: pip install openai-whisper")

def transcribe_audio(audio_path):
    logger.info(f"Transcribing audio file: {audio_path}")
    
    # Get audio duration
    try:
        with wave.open(audio_path, 'rb') as wav_file:
            frames = wav_file.getnframes()
            rate = wav_file.getframerate()
            duration = frames / float(rate)
    except Exception as e:
        logger.error(f"Error getting audio duration: {str(e)}")
        duration = 0
    
    # METHOD 1: Try using Faster Whisper if available (fastest method)
    if FASTER_WHISPER_AVAILABLE:
        try:
            logger.info(f"Using Faster Whisper for transcription")
            start_time = time.time()
            
            # Transcribe the audio (significantly faster than regular whisper)
            segments, info = whisper_model.transcribe(audio_path, beam_size=5, language="en")
            
            # Gather all segments into a single text
            transcribed_text = " ".join([segment.text for segment in segments])
            
            processing_time = time.time() - start_time
            logger.info(f"Faster Whisper transcription completed in {processing_time:.2f} seconds")
            
            return {
                "text": transcribed_text,
                "duration": duration,
                "language": info.language,
                "confidence": 0.9,
                "processing_time": processing_time
            }
        except Exception as e:
            logger.error(f"Faster Whisper transcription error: {str(e)}")
            # Fall back to other methods
    
    # METHOD 2: Try using regular Whisper if available (slower but good quality)
    if WHISPER_AVAILABLE:
        try:
            logger.info(f"Using regular Whisper for transcription")
            start_time = time.time()
            
            # Transcribe the audio
            result = whisper_model.transcribe(audio_path)
            
            # Get the transcribed text
            transcribed_text = result["text"]
            
            processing_time = time.time() - start_time
            logger.info(f"Regular Whisper transcription completed in {processing_time:.2f} seconds")
            
            return {
                "text": transcribed_text,
                "duration": duration,
                "confidence": 0.9,
                "processing_time": processing_time
            }
        except Exception as e:
            logger.error(f"Regular Whisper transcription error: {str(e)}")
    
    
    # METHOD 4: If all else fails, use a fallback message
    logger.warning("All transcription methods failed - returning placeholder text")
    
    placeholder_text = (
        "Không thể thực hiện chuyển đổi âm thanh thành văn bản. "
        "Vui lòng cài đặt thư viện Whisper AI hoặc faster-whisper. "
        "Thời lượng âm thanh khoảng {:.2f} giây.".format(duration)
    )
    
    return {
        "text": placeholder_text,
        "duration": duration,
        "confidence": 0.5,
        "error": "No working transcription methods available"
    }