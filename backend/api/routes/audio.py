import os
import time
import tempfile
import json
from fastapi import APIRouter, File, Form, UploadFile, HTTPException
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
from typing import List
from services.minimax_tts_service import minimax_tts_service
import base64
from services.kokoro_tts_service import kokoro_tts_service
import soundfile as sf

from config import AUDIO_DIR, logger
from models.schemas import CombineAudioRequest
from services.tts_service import infer
from services.video_service import VideoStorage
from utils.audio import validate_audio_file, get_audio_duration
from utils.file_helpers import generate_unique_filename, save_metadata
from pydub import AudioSegment

router = APIRouter()
video_storage = VideoStorage()

def format_timestamp(seconds: float) -> str:
    """Format seconds to SRT timestamp format (HH:MM:SS,mmm)"""
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    milliseconds = (seconds - int(seconds)) * 1000
    return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02},{int(milliseconds):03}"

@router.post("/generate-audio/")
async def generate_audio(
    ref_audio: UploadFile = File(...),
    ref_text: str = Form(...),
    gen_text: str = Form(...),
    remove_silence: bool = Form(False),
    cross_fade_duration: float = Form(0.15),
    speed: float = Form(1.0),
    segment_index: int = Form(None),
    video_id: str = Form(None)
):
    try:
        start_time = time.time()
        temp_path = None
        
        # Update video status if video_id is provided
        if video_id:
            video = video_storage.get_video(video_id)
            if video:
                video_storage.update_video(video_id, {"status": "processing"})
            logger.info(f"Processing audio for video {video_id}")
            
        # Validate input file
        if not validate_audio_file(ref_audio.filename):
            raise HTTPException(status_code=400, detail="Invalid audio file format")

        # Create temporary file for uploaded audio
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_file:
            temp_path = temp_file.name
            contents = await ref_audio.read()
            temp_file.write(contents)

        # Generate unique filename for output
        output_filename = generate_unique_filename()
        output_path = AUDIO_DIR / f"{output_filename}.wav"

        # Process the audio
        infer_result = infer(
            ref_audio_orig=temp_path,
            ref_text=ref_text,
            gen_text=gen_text,
            remove_silence=remove_silence,
            cross_fade_duration=cross_fade_duration,
            speed=speed
        )

        # Extract audio data and sample rate from the tuple
        audio_data, sample_rate, *_ = infer_result
        
        # Save the audio file
        import soundfile as sf
        sf.write(str(output_path), audio_data, sample_rate)

        # Clean up temporary file
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)

        processing_time = time.time() - start_time
        logger.info(f"Audio generation completed in {processing_time:.2f} seconds")

        # Save metadata alongside the audio file
        metadata = {
            "segment_index": segment_index,
            "original_text": gen_text,
            "ref_text": ref_text,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        metadata_path = AUDIO_DIR / f"{output_filename}.json"
        save_metadata(metadata_path, metadata)

        # Update video status on success if video_id is provided
        if video_id and video_storage.get_video(video_id):
            video_storage.update_video(video_id, {"status": "completed"})
            logger.info(f"Completed audio generation for video {video_id}")

        return {
            "audio_path": f"{output_filename}.wav",
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
            
        logger.error(f"Error generating audio: {str(e)}", exc_info=True)
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/combine-audio-segments/")
async def combine_audio_segments(file_paths: List[str]):
    """Combine multiple audio segments into one file"""
    try:
        combined = AudioSegment.empty()
        current_time = 0.0
        gap_duration = 0.1  # 100ms gap between segments
        
        # Create a single entry for each original segment
        srt_entries = []
        
        for i, path in enumerate(file_paths):
            if not os.path.exists(path):
                raise HTTPException(status_code=404, detail=f"Audio file not found: {path}")
            
            # Load audio segment
            segment = AudioSegment.from_wav(path)
            duration = len(segment) / 1000.0  # Convert to seconds
            
            # Get metadata for this segment
            metadata_path = path.rsplit(".", 1)[0] + ".json"
            if not os.path.exists(metadata_path):
                raise HTTPException(status_code=404, detail=f"Metadata not found for segment {i+1}")
            
            with open(metadata_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)
            
            # Add a single SRT entry for this segment
            srt_entries.append({
                "index": i + 1,
                "start_time": format_timestamp(current_time),
                "end_time": format_timestamp(current_time + duration),
                "text": metadata["original_text"].strip()
            })
            
            # Add audio
            combined += segment
            
            # Add gap after all segments except the last one
            if i < len(file_paths) - 1:
                combined += AudioSegment.silent(duration=int(gap_duration * 1000))
                current_time += duration + gap_duration
            else:
                current_time += duration
        
        # Save combined audio
        output_path = AUDIO_DIR / f"combined_{int(time.time())}.wav"
        combined.export(str(output_path), format="wav")
        
        # Generate combined SRT with one entry per segment
        srt_path = str(output_path).rsplit(".", 1)[0] + ".srt"
        srt_content = []
        
        for entry in srt_entries:
            srt_content.extend([
                str(entry["index"]),
                f"{entry['start_time']} --> {entry['end_time']}",
                entry["text"],
                ""  # Empty line between entries
            ])
        
        with open(srt_path, "w", encoding="utf-8") as f:
            f.write("\n".join(srt_content))
        
        return {
            "status": "success",
            "filename": output_path.name,
            "full_path": str(output_path),
            "srt_path": srt_path,
            "total_duration": current_time
        }
    
    except Exception as e:
        logger.error(f"Error combining audio segments: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/combine-audio")
async def combine_audio(request: CombineAudioRequest):
    """Combine multiple audio segments into one file"""
    logger.info(f"Received audio paths: {request.audio_paths}")
    try:
        if not request.audio_paths:
            raise HTTPException(status_code=400, detail="No audio paths provided")

        combined = AudioSegment.empty()
        metadata_list = []
        current_time = 0.0

        for path in request.audio_paths:
            full_path = AUDIO_DIR / path
            if not os.path.exists(full_path):
                raise HTTPException(status_code=404, detail=f"Audio file not found: {path}")
                
            logger.info(f"Adding audio file: {full_path}")
            audio = AudioSegment.from_wav(str(full_path))
            duration = len(audio) / 1000.0  # Convert to seconds

            # Get metadata for this segment
            metadata_path = str(full_path).rsplit(".", 1)[0] + ".json"
            if os.path.exists(metadata_path):
                with open(metadata_path, "r", encoding="utf-8") as f:
                    metadata = json.load(f)
                    metadata["start_time"] = current_time
                    metadata["end_time"] = current_time + duration
                    metadata_list.append(metadata)
            else:
                # Create basic metadata if none exists
                metadata_list.append({
                    "segment_index": len(metadata_list),
                    "original_text": f"Segment {len(metadata_list) + 1}",
                    "start_time": current_time,
                    "end_time": current_time + duration
                })

            combined += audio
            current_time += duration

        # Save combined audio
        timestamp = int(time.time())
        output_filename = f"combined_{timestamp}.wav"
        output_path = AUDIO_DIR / output_filename
        combined.export(str(output_path), format="wav")
        
        # Save combined metadata
        metadata_path = AUDIO_DIR / f"combined_{timestamp}.json"
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump({
                "segments": metadata_list,
                "total_duration": current_time
            }, f, indent=2)
        
        logger.info(f"Successfully combined audio to: {output_path}")
        return {
            "path": f"audio/{output_filename}",
            "duration": current_time,
            "metadata": metadata_list
        }

    except Exception as e:
        logger.error(f"Error in combine_audio: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/audio/{filename}")
async def get_audio(filename: str):
    file_path = AUDIO_DIR / filename
    logger.info(f"Attempting to serve audio file: {file_path}")
    
    if not file_path.exists():
        logger.error(f"Audio file not found: {file_path}")
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    logger.info(f"Serving audio file: {file_path}")
    return FileResponse(
        str(file_path), 
        media_type="audio/wav",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )

@router.post("/generate-audio-minimax/")
async def generate_audio_minimax(
    text: str = Form(...),
    voice_id: str = Form("female-voice-1"),
    speed: float = Form(1.0),
    segment_index: int = Form(None),
    video_id: str = Form(None)
):
    try:
        start_time = time.time()
        
        # Update video status if video_id is provided
        if video_id:
            video = video_storage.get_video(video_id)
            if video:
                video_storage.update_video(video_id, {"status": "processing"})
            logger.info(f"Processing audio for video {video_id}")
        
        # Generate unique filename for output
        output_filename = generate_unique_filename()
        output_path = AUDIO_DIR / f"{output_filename}.wav"
        
        # Generate audio using MiniMax service
        audio_data_base64, sample_rate = minimax_tts_service.generate_speech(
            text=text,
            voice_id=voice_id,
            speed=speed
        )
        
        # Decode base64 to bytes
        audio_data = base64.b64decode(audio_data_base64)
        
        # Save the audio file
        with open(output_path, "wb") as f:
            f.write(audio_data)
            
        processing_time = time.time() - start_time
        logger.info(f"MiniMax audio generation completed in {processing_time:.2f} seconds")
        
        # Save metadata alongside the audio file
        metadata = {
            "segment_index": segment_index,
            "original_text": text,
            "voice_id": voice_id,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "source": "minimax"
        }
        
        metadata_path = AUDIO_DIR / f"{output_filename}.json"
        save_metadata(metadata_path, metadata)
        
        # Update video status on success if video_id is provided
        if video_id and video_storage.get_video(video_id):
            video_storage.update_video(video_id, {"status": "completed"})
            logger.info(f"Completed audio generation for video {video_id}")
            
        return {
            "audio_path": f"{output_filename}.wav",
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
            
        logger.error(f"Error generating audio with MiniMax: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/minimax-voices/")
async def get_minimax_voices():
    """Get available voices from MiniMax TTS service"""
    try:
        voices = minimax_tts_service.get_available_voices()
        return voices
    except Exception as e:
        logger.error(f"Error getting MiniMax voices: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/generate-audio-kokoro/")
async def generate_audio_kokoro(
    text: str = Form(...),
    speaker_id: str = Form("default"),
    speed: float = Form(1.0),
    segment_index: int = Form(None),
    video_id: str = Form(None)
):
    try:
        start_time = time.time()
        
        # Update video status if video_id is provided
        if video_id:
            video = video_storage.get_video(video_id)
            if video:
                video_storage.update_video(video_id, {"status": "processing"})
            logger.info(f"Processing audio for video {video_id}")
        
        # Generate unique filename for output
        output_filename = generate_unique_filename()
        output_path = AUDIO_DIR / f"{output_filename}.wav"
        
        # Generate audio using Kokoro service
        audio_data, sample_rate = kokoro_tts_service.generate_speech(
            text=text,
            speaker_id=speaker_id,
            speed=speed
        )
        
        # Save the audio file
        sf.write(str(output_path), audio_data, sample_rate)
            
        processing_time = time.time() - start_time
        logger.info(f"Kokoro audio generation completed in {processing_time:.2f} seconds")
        
        # Save metadata alongside the audio file
        metadata = {
            "segment_index": segment_index,
            "original_text": text,
            "speaker_id": speaker_id,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "source": "kokoro"
        }
        
        metadata_path = AUDIO_DIR / f"{output_filename}.json"
        save_metadata(metadata_path, metadata)
        
        # Update video status on success if video_id is provided
        if video_id and video_storage.get_video(video_id):
            video_storage.update_video(video_id, {"status": "completed"})
            logger.info(f"Completed audio generation for video {video_id}")
            
        return {
            "audio_path": f"{output_filename}.wav",
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

@router.get("/kokoro-speakers/")
async def get_kokoro_speakers():
    """Get available speakers from Kokoro TTS service"""
    try:
        speakers = kokoro_tts_service.get_available_speakers()
        return speakers
    except Exception as e:
        logger.error(f"Error getting Kokoro speakers: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))