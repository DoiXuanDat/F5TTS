from fastapi import APIRouter, Form, HTTPException
import time
from services.official_kokoro_tts_service import official_kokoro_tts_service
from config import AUDIO_DIR, logger
from utils.file_helpers import save_metadata
from services.video_service import video_storage

router = APIRouter()

@router.get("/kokoro-speakers/")
async def get_kokoro_speakers():
    """Get list of available Kokoro TTS speakers"""
    try:
        speakers = official_kokoro_tts_service.get_available_voices()
        logger.info(f"Returned {len(speakers)} speakers from Kokoro TTS")
        return speakers
    except Exception as e:
        logger.error(f"Error getting Kokoro speakers: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/generate-audio-kokoro/")
async def generate_audio_kokoro(
    text: str = Form(...),
    speaker_id: str = Form("af_sarah"),
    speed: float = Form(1.0),
    segment_index: int = Form(None),
    video_id: str = Form(None)
):
    """Generate audio using Kokoro TTS"""
    try:
        start_time = time.time()
        
        # Update video status if video_id is provided
        if video_id:
            video = video_storage.get_video(video_id)
            if video:
                video_storage.update_video(video_id, {"status": "processing"})
            logger.info(f"Processing audio for video {video_id}")
        
        # Generate speech with Kokoro service
        audio_data, sample_rate, relative_path = official_kokoro_tts_service.generate_speech(
            text=text,
            speaker_id=speaker_id,
            speed=speed
        )
        
        # Extract filename from relative path
        output_filename = relative_path.split('/')[-1]
            
        processing_time = time.time() - start_time
        logger.info(f"Kokoro TTS audio generation completed in {processing_time:.2f} seconds")
        
        # Save metadata alongside the audio file
        metadata = {
            "segment_index": segment_index,
            "original_text": text,
            "speaker_id": speaker_id,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "source": "kokoro"
        }
        
        metadata_path = AUDIO_DIR / f"{output_filename.split('.')[0]}.json"
        save_metadata(metadata_path, metadata)
        
        # Update video status on success if video_id is provided
        if video_id and video_storage.get_video(video_id):
            video_storage.update_video(video_id, {"status": "completed"})
            logger.info(f"Completed audio generation for video {video_id}")
            
        return {
            "audio_path": output_filename,
            "status": "success",
            "processing_time": processing_time,
            "metadata": metadata,
            "video_id": video_id
        }
        
    except Exception as e:
        # Update video status on error if video_id is provided
        if video_id and video_storage.get_video(video_id):
            video_storage.update_video(video_id, {"status": "error", "error": str(e)})
            logger.error(f"Error generating audio for video {video_id}: {str(e)}")
            
        logger.error(f"Error generating audio with Kokoro: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))