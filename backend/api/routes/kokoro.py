from fastapi import APIRouter, Form, HTTPException
import uuid
import soundfile as sf
from services.kokoro_tts_service import kokoro_tts_service
from config import BASE_DIR, AUDIO_DIR

router = APIRouter(prefix="/kokoro", tags=["Kokoro TTS"])

@router.get("/speakers/")
async def get_kokoro_speakers():
    """Get list of available Kokoro TTS speakers"""
    speakers = kokoro_tts_service.get_available_speakers()
    return speakers

@router.post("/generate-audio/")
async def generate_audio_kokoro(
    text: str = Form(...),
    speaker_id: str = Form("default"),
    speed: float = Form(1.0)
):
    """Generate audio using Kokoro TTS"""
    try:
        audio_data, sample_rate = kokoro_tts_service.generate_speech(
            text=text,
            speaker_id=speaker_id,
            speed=speed
        )
        
        # Save audio to a file
        file_name = f"kokoro_{uuid.uuid4()}.wav"
        output_path = AUDIO_DIR / file_name
        sf.write(str(output_path), audio_data, sample_rate)
        
        return {
            "success": True,
            "audio_path": str(output_path.relative_to(BASE_DIR)),
            "duration": len(audio_data) / sample_rate
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))