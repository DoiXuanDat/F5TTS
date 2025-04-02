import os
import tempfile
import soundfile as sf
import numpy as np
from pathlib import Path
import uuid
import logging
import sys
import traceback

from config import logger, BASE_DIR, AUDIO_DIR

class DirectKokoroTTSService:
    """
    Service for text-to-speech using the kokoro_onnx library directly
    instead of calling the kokoro-tts.py script
    """
    
    def __init__(self):
        # Set paths to the model files
        self.kokoro_dir = Path(os.environ.get("KOKORO_TTS_PATH", "D:/F5-TTS/kokoro-tts"))
        self.model_path = self.kokoro_dir / "kokoro-v1.0.onnx"
        self.voices_path = self.kokoro_dir / "voices-v1.0.bin"
        
        # Verify model files exist
        if not (self.model_path.exists() and self.voices_path.exists()):
            logger.error("Required Kokoro model files missing (kokoro-v1.0.onnx or voices-v1.0.bin)")
            logger.error(f"Expected path for model: {self.model_path}")
            logger.error(f"Expected path for voices: {self.voices_path}")
            logger.info("Please download the model files from https://github.com/nazdridoy/kokoro-tts")
            
        logger.info(f"Direct Kokoro TTS service initialized with path: {self.kokoro_dir}")
        
        # Initialize the Kokoro model
        self._kokoro = None
        
    def _get_kokoro(self):
        """Get or create the Kokoro model instance"""
        if self._kokoro is None:
            try:
                from kokoro_onnx import Kokoro
                self._kokoro = Kokoro(str(self.model_path), str(self.voices_path))
                logger.info("Successfully initialized Kokoro model")
            except Exception as e:
                logger.error(f"Error initializing Kokoro model: {e}")
                logger.error(traceback.format_exc())
                raise RuntimeError(f"Failed to initialize Kokoro model: {e}")
        return self._kokoro
                
    def generate_speech(self, text, speaker_id="af_sarah", speed=1.0):
        """
        Generate speech using the kokoro_onnx library directly
        
        Args:
            text: Text to synthesize
            speaker_id: Speaker ID/voice to use
            speed: Speech speed multiplier
            
        Returns:
            tuple: (audio_data, sample_rate, relative_path)
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")
            
        # Generate a unique filename for output
        output_filename = f"kokoro_{uuid.uuid4()}.wav"
        output_path = AUDIO_DIR / output_filename
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            # Get the Kokoro model
            kokoro = self._get_kokoro()
            
            # Set default language
            lang = "en-us"
            
            logger.info(f"Generating speech with Kokoro for text: {text[:50]}...")
            logger.info(f"Using voice: {speaker_id}, speed: {speed}")
            
            # Generate speech
            audio_data, sample_rate = kokoro.create(text, voice=speaker_id, speed=speed, lang=lang)
            
            # Save the audio file
            sf.write(str(output_path), audio_data, sample_rate)
            
            # Get relative path for frontend
            relative_path = output_path.relative_to(BASE_DIR)
            
            logger.info(f"Successfully generated audio with Kokoro: {output_filename}")
            
            return audio_data, sample_rate, str(relative_path)
            
        except Exception as e:
            logger.error(f"Error generating speech with Kokoro: {e}")
            logger.error(traceback.format_exc())
            raise
    
    def get_available_voices(self):
        """Get list of available voices from Kokoro or use hardcoded list"""
        try:
            # Try to get voices directly from Kokoro
            kokoro = self._get_kokoro()
            voices = kokoro.get_voices()
            
            # Convert to the expected format
            return [
                {"id": voice_id, "name": self._get_display_name(voice_id)}
                for voice_id in voices
            ]
        except Exception as e:
            logger.error(f"Error getting voices from Kokoro: {e}")
            logger.info("Falling back to hardcoded voice list")
            
            # Return hardcoded list if Kokoro fails
            return [
                {"id": "af_sarah", "name": "Sarah (Female, US)"},
                {"id": "af_bella", "name": "Bella (Female, US)"},
                {"id": "af_heart", "name": "Heart (Female, US)"},
                {"id": "af_jessica", "name": "Jessica (Female, US)"},
                {"id": "af_nicole", "name": "Nicole (Female, US)"},
                {"id": "af_alloy", "name": "Alloy (Female, US)"},
                {"id": "af_aoede", "name": "Aoede (Female, US)"},
                {"id": "af_kore", "name": "Kore (Female, US)"},
                {"id": "af_nova", "name": "Nova (Female, US)"},
                {"id": "af_river", "name": "River (Female, US)"},
                {"id": "af_sky", "name": "Sky (Female, US)"},
                {"id": "am_adam", "name": "Adam (Male, US)"},
                {"id": "am_echo", "name": "Echo (Male, US)"},
                {"id": "am_eric", "name": "Eric (Male, US)"},
                {"id": "am_fenrir", "name": "Fenrir (Male, US)"},
                {"id": "am_liam", "name": "Liam (Male, US)"},
                {"id": "am_michael", "name": "Michael (Male, US)"},
                {"id": "am_onyx", "name": "Onyx (Male, US)"},
                {"id": "am_puck", "name": "Puck (Male, US)"},
                {"id": "bf_alice", "name": "Alice (Female, UK)"},
                {"id": "bf_emma", "name": "Emma (Female, UK)"},
                {"id": "bf_isabella", "name": "Isabella (Female, UK)"},
                {"id": "bf_lily", "name": "Lily (Female, UK)"},
                {"id": "bm_daniel", "name": "Daniel (Male, UK)"},
                {"id": "bm_fable", "name": "Fable (Male, UK)"},
                {"id": "bm_george", "name": "George (Male, UK)"},
                {"id": "bm_lewis", "name": "Lewis (Male, UK)"},
                {"id": "ff_siwis", "name": "Siwis (Female, French)"},
                {"id": "if_sara", "name": "Sara (Female, Italian)"},
                {"id": "im_nicola", "name": "Nicola (Male, Italian)"},
                {"id": "jf_alpha", "name": "Alpha (Female, Japanese)"},
                {"id": "jf_gongitsune", "name": "Gongitsune (Female, Japanese)"},
                {"id": "jf_nezumi", "name": "Nezumi (Female, Japanese)"},
                {"id": "jf_tebukuro", "name": "Tebukuro (Female, Japanese)"},
                {"id": "jm_kumo", "name": "Kumo (Male, Japanese)"},
                {"id": "zf_xiaobei", "name": "Xiaobei (Female, Chinese)"},
                {"id": "zf_xiaoni", "name": "Xiaoni (Female, Chinese)"},
                {"id": "zf_xiaoxiao", "name": "Xiaoxiao (Female, Chinese)"},
                {"id": "zf_xiaoyi", "name": "Xiaoyi (Female, Chinese)"},
                {"id": "zm_yunjian", "name": "Yunjian (Male, Chinese)"},
                {"id": "zm_yunxi", "name": "Yunxi (Male, Chinese)"},
                {"id": "zm_yunxia", "name": "Yunxia (Male, Chinese)"},
                {"id": "zm_yunyang", "name": "Yunyang (Male, Chinese)"}
            ]
    
    def get_available_speakers(self):
        """Alias for get_available_voices to maintain compatibility"""
        return self.get_available_voices()
    
    def _get_display_name(self, voice_id):
        """Convert voice ID to a display name"""
        # Parse the voice ID format (e.g., af_sarah, am_adam, etc.)
        try:
            # First character: gender (a: American, b: British, etc.)
            # Second character: gender (f: female, m: male)
            # Rest: name
            
            if not voice_id or len(voice_id) < 4:
                return voice_id
                
            region_code = voice_id[0]
            gender_code = voice_id[1]
            name = voice_id[3:].capitalize()
            
            region_map = {
                'a': 'US',
                'b': 'UK',
                'j': 'Japanese',
                'z': 'Chinese',
                'i': 'Italian',
                'f': 'French'
            }
            
            gender_map = {
                'f': 'Female',
                'm': 'Male'
            }
            
            region = region_map.get(region_code, "")
            gender = gender_map.get(gender_code, "")
            
            return f"{name} ({gender}, {region})"
            
        except Exception:
            # If parsing fails, just return the voice ID
            return voice_id
            
# Initialize the service
official_kokoro_tts_service = DirectKokoroTTSService()