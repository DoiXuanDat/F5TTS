# First, consolidate your imports at the top
import logging
import time
import re
import tempfile
import os
import json
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum
from typing import List, Optional, Dict
from io import BytesIO

# Third-party imports
import soundfile as sf
import torchaudio
from cached_path import cached_path
from num2words import num2words
import numpy as np
from pydub import AudioSegment

# FastAPI imports
from fastapi import FastAPI, File, UploadFile, HTTPException, Form, Body
from fastapi.responses import FileResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# F5 TTS model imports
from f5_tts.model import DiT
from f5_tts.infer.utils_infer import (
    load_vocoder,
    load_model,
    infer_process,
    remove_silence_for_generated_wav,
    save_spectrogram,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Define base directory for audio files
BASE_DIR = Path(__file__).parent
AUDIO_DIR = BASE_DIR / "generated_audio_files"
if not AUDIO_DIR.exists():
    AUDIO_DIR.mkdir(parents=True)

# Define Pydantic models
class VideoStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"

class VideoCreate(BaseModel):
    title: str
    audioPath: str
    srtPath: Optional[str] = None

class Video(BaseModel):
    id: str
    title: str
    status: str = 'pending'
    createdAt: datetime = None
    url: Optional[str] = None
    error: Optional[str] = None
    metadata: Optional[dict] = None

    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }

class VideoUpdate(BaseModel):
    status: Optional[VideoStatus] = None
    error: Optional[str] = None
    url: Optional[str] = None

class AudioPaths(BaseModel):
    paths: List[str]

class CombineAudioRequest(BaseModel):
    audio_paths: List[str]

class SRTRequest(BaseModel):
    audio_paths: List[str]

# Define VideoStorage class
class VideoStorage:
    def __init__(self):
        self.storage_file = AUDIO_DIR / "videos.json"
        self.videos: Dict[str, Video] = {}
        self._init_storage()
        self.load_videos()

    def _init_storage(self):
        if not self.storage_file.parent.exists():
            self.storage_file.parent.mkdir(parents=True)
        
        if not self.storage_file.exists():
            with open(self.storage_file, 'w', encoding='utf-8') as f:
                json.dump([], f)

    def load_videos(self):
        try:
            with open(self.storage_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for video_data in data:
                    if 'createdAt' in video_data and video_data['createdAt']:
                        video_data['createdAt'] = datetime.fromisoformat(video_data['createdAt'])
                    video = Video(**video_data)
                    self.videos[video.id] = video
        except json.JSONDecodeError:
            with open(self.storage_file, 'w', encoding='utf-8') as f:
                json.dump([], f)

    def save_videos(self):
        videos_data = [video.dict() for video in self.videos.values()]
        with open(self.storage_file, 'w', encoding='utf-8') as f:
            json.dump(videos_data, f, indent=2, default=self._json_serializer)

    def _json_serializer(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f'Type {type(obj)} not serializable')

    def add_video(self, video: Video) -> Video:
        self.videos[video.id] = video
        self.save_videos()
        return video

    def get_video(self, video_id: str) -> Optional[Video]:
        return self.videos.get(video_id)

    def update_video(self, video_id: str, updates: dict) -> Optional[Video]:
        if video_id not in self.videos:
            return None
        
        video = self.videos[video_id]
        for key, value in updates.items():
            if hasattr(video, key):
                setattr(video, key, value)
                
        self.save_videos()
        return video

    def get_all_videos(self) -> List[Video]:
        return list(self.videos.values())

    def remove_video(self, video_id: str) -> bool:
        if video_id in self.videos:
            del self.videos[video_id]
            self.save_videos()
            return True
        return False

# Utility functions
def validate_audio_file(filename):
    """Validate audio file type"""
    allowed_extensions = {'.wav'}
    return os.path.splitext(filename)[1].lower() in allowed_extensions

def get_audio_duration(audio_path):
    """Get exact duration of audio file in seconds"""
    audio = AudioSegment.from_wav(audio_path)
    return len(audio) / 1000.0

def format_timestamp(seconds):
    """Format seconds into SRT timestamp format"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:06.3f}".replace(".", ",")

def scale_timestamps(segments, actual_duration, original_duration):
    """Scale timestamps to match actual audio duration with improved precision"""
    if original_duration == 0:
        return segments
    
    # Calculate scale factor with higher precision
    scale_factor = actual_duration / original_duration
    logger.info(f"Scaling timestamps by factor: {scale_factor:.6f}")
    
    adjusted_segments = []
    cumulative_error = 0
    
    for i, segment in enumerate(segments):
        # Apply scaling with error correction
        start = segment["start"] * scale_factor
        end = segment["end"] * scale_factor
        
        # Adjust for cumulative rounding errors
        start = max(0, start - cumulative_error)
        end = min(actual_duration, end - cumulative_error)
        
        # Update cumulative error
        expected_duration = (segment["end"] - segment["start"]) * scale_factor
        actual_segment_duration = end - start
        cumulative_error += actual_segment_duration - expected_duration
        
        adjusted_segments.append({
            "start": start,
            "end": end,
            "text": segment["text"]
        })
    
    return adjusted_segments

def generate_synchronized_srt(audio_path, segment_info):
    """Generate SRT file with timestamps synchronized to actual audio duration"""
    try:
        logger.info(f"Generating synchronized SRT for: {audio_path}")
        
        actual_duration = get_audio_duration(audio_path)
        logger.info(f"Actual audio duration: {actual_duration} seconds")
        
        if not segment_info or "original_text" not in segment_info:
            raise Exception("Segment info with original text is required")
        
        # Create a single SRT entry for the entire segment text
        srt_content = [
            "1",  # Always 1 because there's only one entry
            f"{format_timestamp(0.0)} --> {format_timestamp(actual_duration)}",
            segment_info["original_text"].strip(),  # Use the original text
            ""
        ]
        
        base_path = audio_path.rsplit(".", 1)[0]
        srt_path = f"{base_path}.srt"
        
        with open(srt_path, "w", encoding="utf-8") as f:
            f.write("\n".join(srt_content))
        
        # Save metadata for future use when combining
        metadata = {
            "segment_index": segment_info["segment_index"],
            "original_text": segment_info["original_text"],
            "actual_duration": actual_duration,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        metadata_path = f"{base_path}.json"
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)
        
        return srt_path
    except Exception as e:
        logger.error(f"Error generating synchronized SRT: {str(e)}", exc_info=True)
        raise Exception(f"Failed to generate synchronized SRT: {str(e)}")

def translate_number_to_text(text):
    """Convert numbers to words in text"""
    text_separated = re.sub(r'([A-Za-z])(\d)', r'\1 \2', text)
    text_separated = re.sub(r'(\d)([A-Za-z])', r'\1 \2', text_separated)
    
    def replace_number(match):
        number = match.group()
        return num2words(int(number), lang='en')
    
    return re.sub(r'\b\d+\b', replace_number, text_separated)

# Check if GPU decorator is available
try:
    import spaces
    USING_SPACES = True
except ImportError:
    USING_SPACES = False

def gpu_decorator(func):
    if USING_SPACES:
        return spaces.GPU(func)
    return func

# Load TTS models
vocoder = load_vocoder()
F5TTS_model_cfg = dict(dim=1024, depth=22, heads=16, ff_mult=2, text_dim=512, conv_layers=4)
F5TTS_ema_model = load_model(
    DiT, 
    F5TTS_model_cfg, 
    str(cached_path("hf://SWivid/F5-TTS/F5TTS_Base/model_1200000.safetensors"))
)

@gpu_decorator
def infer(ref_audio_orig, ref_text, gen_text, remove_silence=False, cross_fade_duration=0.15, speed=1.0, nfe_step=8):
    """Generate audio using F5-TTS model"""
    logger.info("Starting text preprocessing...")
    gen_text = gen_text.lower()
    gen_text = translate_number_to_text(gen_text)
    
    # Inference process
    final_wave, final_sample_rate, combined_spectrogram = infer_process(
        ref_audio_orig, ref_text, gen_text, F5TTS_ema_model, vocoder,
        cross_fade_duration=cross_fade_duration, speed=speed, nfe_step=nfe_step
    )
    
    # Remove silence if requested
    if remove_silence:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_wave:
            sf.write(tmp_wave.name, final_wave, final_sample_rate)
            remove_silence_for_generated_wav(tmp_wave.name)
            final_wave, _ = torchaudio.load(tmp_wave.name)
        final_wave = final_wave.squeeze().cpu().numpy()
    
    # Save spectrogram
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_spectrogram:
        spectrogram_path = tmp_spectrogram.name
        save_spectrogram(combined_spectrogram, spectrogram_path)
    
    logger.info("Inference completed successfully.")
    return final_wave, final_sample_rate, spectrogram_path

# Initialize FastAPI app
app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"]
)

# Mount static files directory
app.mount("/audio", StaticFiles(directory=str(AUDIO_DIR)), name="audio")

# Initialize video storage
video_storage = VideoStorage()

# API Routes
@app.post("/generate-audio/")
async def generate_audio(
    ref_audio: UploadFile = File(...),
    ref_text: str = Form(...),
    gen_text: str = Form(...),
    remove_silence: bool = Form(False),
    cross_fade_duration: float = Form(0.15),
    speed: float = Form(1.0),
    segment_index: int = Form(None),
    video_id: Optional[str] = Form(None)
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
        output_filename = f"{int(time.time() * 1000)}"
        output_path = AUDIO_DIR / f"generated_audio_{output_filename}.wav"

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
        
        # Convert audio data to the correct format and save
        if isinstance(audio_data, np.ndarray):
            sf.write(str(output_path), audio_data, sample_rate)
        else:
            logger.error(f"Unexpected audio data type: {type(audio_data)}")
            raise ValueError("Invalid audio data format")

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
        
        metadata_path = AUDIO_DIR / f"generated_audio_{output_filename}.json"
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        # Update video status on success if video_id is provided
        if video_id and video_storage.get_video(video_id):
            video_storage.update_video(video_id, {"status": "completed"})
            logger.info(f"Completed audio generation for video {video_id}")

        return {
            "audio_path": f"generated_audio_{output_filename}.wav",
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

@app.post("/combine-audio-segments/")
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

@app.post("/generate-combined-srt")
async def generate_combined_srt(request: SRTRequest):
    try:
        logger.info(f"Received request with paths: {request.audio_paths}")
        srt_entries = []
        
        for path in request.audio_paths:
            full_path = AUDIO_DIR / path
            metadata_path = str(full_path).rsplit(".", 1)[0] + ".json"
            
            if not os.path.exists(metadata_path):
                logger.error(f"Metadata file not found: {metadata_path}")
                continue
                
            with open(metadata_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)
                
            # Get audio duration for verification
            audio = AudioSegment.from_wav(str(full_path))
            duration = len(audio) / 1000.0
            
            srt_entries.append({
                "index": metadata.get("segment_index", len(srt_entries) + 1),
                "start_time": format_timestamp(0),
                "end_time": format_timestamp(duration),
                "text": metadata.get("original_text", f"Segment {len(srt_entries) + 1}")
            })

        # Generate SRT content
        srt_content = []
        for entry in srt_entries:
            srt_content.extend([
                str(entry["index"]),
                f"{entry['start_time']} --> {entry['end_time']}", 
                entry["text"],
                ""
            ])

        srt_text = "\n".join(srt_content)
        
        return Response(
            content=srt_text,
            media_type="text/plain",
            headers={
                "Content-Disposition": "attachment; filename=combined.srt"
            }
        )

    except Exception as e:
        logger.error(f"Error generating SRT: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate SRT: {str(e)}"
        )

@app.post("/combine-audio")
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

@app.get("/audio/{filename}")
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

@app.get("/videos/")
async def list_videos():
    try:
        videos = video_storage.get_all_videos()
        logger.info(f"Retrieved {len(videos)} videos")
        return videos
    except Exception as e:
        logger.error(f"Error retrieving videos: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/videos/")
async def create_video(video: VideoCreate):
    try:
        video_id = f"VID{int(time.time() * 1000)}"
        new_video = Video(
            id=video_id,
            title=video.title,
            status="pending",
            createdAt=datetime.now(),
            url=video.audioPath,
            metadata={"srtPath": video.srtPath} if video.srtPath else None
        )
        stored_video = video_storage.add_video(new_video)
        logger.info(f"Created new video with ID: {video_id}")
        return stored_video
    except Exception as e:
        logger.error(f"Error creating video: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/videos/{video_id}")
async def get_video(video_id: str):
    try:
        video = video_storage.get_video(video_id)
        if not video:
            raise HTTPException(status_code=404, detail="Video not found")
        return video
    except Exception as e:
        logger.error(f"Error getting video: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.patch("/videos/{video_id}")
async def update_video(video_id: str, video_update: VideoUpdate):
    try:
        updated_video = video_storage.update_video(video_id, video_update.dict(exclude_unset=True))
        if not updated_video:
            raise HTTPException(status_code=404, detail="Video not found")
        return updated_video
    except Exception as e:
        logger.error(f"Error updating video: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/videos/{video_id}")
async def delete_video(video_id: str):
    try:
        if video_storage.remove_video(video_id):
            return {"status": "success", "message": "Video deleted successfully"}
        raise HTTPException(status_code=404, detail="Video not found")
    except Exception as e:
        logger.error(f"Error deleting video: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))