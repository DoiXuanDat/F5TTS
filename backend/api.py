import uuid
from fastapi import FastAPI, Form, HTTPException
from services.kokoro_tts_service import kokoro_tts_service
from config import BASE_DIR, AUDIO_DIR
import soundfile as sf
import logging

# Configure logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

@app.get("/kokoro-speakers/")
async def get_kokoro_speakers():
    """Get list of available Kokoro TTS speakers"""
    speakers = kokoro_tts_service.get_available_speakers()
    return speakers


@app.post("/generate-audio-kokoro/")
async def generate_audio_kokoro(
    text: str = Form(...),
    speaker_id: str = Form("default"),
    speed: float = Form(1.0)
):
    """Generate audio using Kokoro TTS"""
    try:
        # Validate input
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")
        
        # Generate speech with updated service method
        audio_data, sample_rate, relative_path = kokoro_tts_service.generate_speech(
            text=text,
            speaker_id=speaker_id,
            speed=speed
        )
        
        # Calculate duration
        duration = len(audio_data) / sample_rate
        
        return {
            "success": True,
            "audio_path": relative_path,
            "duration": duration
        }
    except Exception as e:
        logger.error(f"Kokoro TTS generation error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))