import logging
import time
import re
import tempfile
import soundfile as sf
import torchaudio
from cached_path import cached_path
from num2words import num2words
from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.responses import FileResponse
from datetime import timedelta
import os
from pydub import AudioSegment
import json
from typing import List

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

# FastAPI initialization
app = FastAPI()

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

# Load models
vocoder = load_vocoder()
F5TTS_model_cfg = dict(dim=1024, depth=22, heads=16, ff_mult=2, text_dim=512, conv_layers=4)
F5TTS_ema_model = load_model(
    DiT, 
    F5TTS_model_cfg, 
    str(cached_path("hf://SWivid/F5-TTS/F5TTS_Base/model_1200000.safetensors"))
)

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
        
        # Tạo một entry SRT duy nhất cho toàn bộ segment text
        srt_content = [
            "1",  # Luôn là 1 vì chỉ có một entry
            f"{format_timestamp(0.0)} --> {format_timestamp(actual_duration)}",
            segment_info["original_text"].strip(),  # Sử dụng nguyên text gốc
            ""
        ]
        
        base_path = audio_path.rsplit(".", 1)[0]
        srt_path = f"{base_path}.srt"
        
        with open(srt_path, "w", encoding="utf-8") as f:
            f.write("\n".join(srt_content))
        
        # Save metadata để sử dụng khi combine
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

@gpu_decorator
def infer(ref_audio_orig, ref_text, gen_text, remove_silence=False, cross_fade_duration=0.15, speed=1.0, nfe_step=32):
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

@app.post("/generate-audio/")
async def generate_audio(
    ref_audio: UploadFile = File(...),
    ref_text: str = Form(...),
    gen_text: str = Form(...),
    remove_silence: bool = Form(False),
    cross_fade_duration: float = Form(0.15),
    speed: float = Form(1.0),
    segment_index: int = Form(None)
):
    """Generate audio and synchronized SRT for a segment"""
    start_time = time.time()
    try:
        # Input validation
        if not ref_audio.filename.endswith(".wav"):
            raise HTTPException(status_code=400, detail="The audio file must be in WAV format.")
        
        # Save reference audio
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_audio:
            tmp_audio.write(ref_audio.file.read())
            ref_audio_path = tmp_audio.name
        
        # Generate audio
        final_wave, final_sample_rate, _ = infer(
            ref_audio_path, ref_text, gen_text, remove_silence, cross_fade_duration, speed
        )
        
        # Save generated audio
        output_dir = "/app/generated_audio_files"
        os.makedirs(output_dir, exist_ok=True)
        
        segment_suffix = f"_segment_{segment_index}" if segment_index is not None else ""
        output_filename = f"generated_audio_{int(time.time())}{segment_suffix}.wav"
        output_path = os.path.join(output_dir, output_filename)
        
        sf.write(output_path, final_wave, final_sample_rate)
        
        # Generate SRT for this segment
        if segment_index is not None:
            segment_info = {
                "segment_index": segment_index,
                "original_text": gen_text,  # Use exact text from user input
                "inference_params": {
                    "remove_silence": remove_silence,
                    "cross_fade_duration": cross_fade_duration,
                    "speed": speed
                }
            }
            srt_path = generate_synchronized_srt(output_path, segment_info)
        
        execution_time = time.time() - start_time
        logger.info(f"Total execution time: {execution_time:.2f} seconds")
        
        return {
            "status": "success",
            "filename": output_filename,
            "full_path": output_path,
            "execution_time": execution_time,
            "srt_path": srt_path if segment_index is not None else None
        }
        
    except Exception as e:
        logger.error(f"Error generating audio: {str(e)}", exc_info=True)
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
        output_path = os.path.join("/app/generated_audio_files", f"combined_{int(time.time())}.wav")
        combined.export(output_path, format="wav")
        
        # Generate combined SRT with one entry per segment
        srt_path = output_path.rsplit(".", 1)[0] + ".srt"
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
            "filename": os.path.basename(output_path),
            "full_path": output_path,
            "srt_path": srt_path,
            "total_duration": current_time
        }
    
    except Exception as e:
        logger.error(f"Error combining audio segments: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    

@app.post("/generate-combined-srt/")
async def generate_combined_srt(file_paths: List[str]):
    """Generate combined SRT file from multiple audio segments"""
    try:
        logger.info(f"Starting combined SRT generation for {len(file_paths)} files")
        
        # Validate input paths
        for path in file_paths:
            if not os.path.exists(path):
                raise HTTPException(status_code=404, detail=f"Audio file not found: {path}")
        
        srt_segments = []
        current_time = 0.0
        gap_duration = 0.1  # 100ms gap between segments
        
        for i, audio_path in enumerate(file_paths):
            # Get audio duration
            duration = get_audio_duration(audio_path)
            
            # Get original text from metadata file
            metadata_path = audio_path.rsplit(".", 1)[0] + ".json"
            original_text = ""
            if os.path.exists(metadata_path):
                with open(metadata_path, "r", encoding="utf-8") as f:
                    metadata = json.load(f)
                    original_text = metadata.get("original_text", "")
            
            # Add segment to SRT content
            srt_segments.extend([
                str(i + 1),  # Segment number
                f"{format_timestamp(current_time)} --> {format_timestamp(current_time + duration)}",
                original_text.strip(),
                ""  # Empty line between segments
            ])
            
            # Update timing for next segment
            current_time += duration + gap_duration
        
        # Generate output path
        output_dir = "/app/generated_audio_files"
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"combined_{int(time.time())}.srt")
        
        # Write combined SRT
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(srt_segments))
        
        logger.info(f"Successfully generated combined SRT: {output_path}")
        
        return FileResponse(
            path=output_path,
            filename=os.path.basename(output_path),
            media_type="application/x-subrip"
        )
        
    except Exception as e:
        logger.error(f"Error generating combined SRT: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))