# backend/api/routes/transcription.py
import os
import tempfile
import time
import logging
from pathlib import Path
from fastapi import APIRouter, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydub import AudioSegment

from config import logger
from services.transcription_service import transcribe_audio

router = APIRouter()

@router.post("/transcribe-audio/")
async def transcribe_audio_file(
    background_tasks: BackgroundTasks,
    audio: UploadFile = File(...)
):
    """
    Transcribe an audio file to text.
    Supports .wav and .mp3 files.
    """
    try:
        # Validate file type
        filename = audio.filename.lower()
        if not (filename.endswith('.wav') or filename.endswith('.mp3')):
            raise HTTPException(
                status_code=400, 
                detail="Only .wav and .mp3 files are supported"
            )
            
        logger.info(f"Received audio file for transcription: {filename}")
        
        # Create temporary file to store uploaded audio
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1]) as temp_file:
            temp_path = temp_file.name
            
            # Save uploaded file to temp file
            content = await audio.read()
            temp_file.write(content)
        
        logger.info(f"Saved audio to temporary file: {temp_path}")
        
        # Process audio file based on type
        try:
            # Convert mp3 to wav if needed
            if filename.endswith('.mp3'):
                logger.info("Converting MP3 to WAV for processing")
                audio_segment = AudioSegment.from_mp3(temp_path)
                wav_path = temp_path.replace('.mp3', '.wav')
                audio_segment.export(wav_path, format="wav")
                os.unlink(temp_path)  # Remove the original mp3
                temp_path = wav_path
                logger.info(f"Converted to WAV: {wav_path}")
            
            # Start transcription
            logger.info("Starting transcription process")
            
            # Use the transcription service
            transcription_result = transcribe_audio(temp_path)
            
            # Clean up temp file in the background
            background_tasks.add_task(os.unlink, temp_path)
            
            return {
                "success": True,
                "text": transcription_result["text"],
                "duration": transcription_result.get("duration", 0),
                "confidence": transcription_result.get("confidence", 0)
            }
            
        except Exception as process_error:
            logger.error(f"Error processing audio: {str(process_error)}", exc_info=True)
            # Clean up temp file
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise HTTPException(
                status_code=500, 
                detail=f"Failed to process audio: {str(process_error)}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Transcription error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail=f"Transcription failed: {str(e)}"
        )