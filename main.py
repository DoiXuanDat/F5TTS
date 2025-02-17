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
import whisper
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
whisper_model = whisper.load_model("base")

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

def generate_synchronized_srt(audio_path, segment_info=None):
    """Generate SRT file with timestamps synchronized to actual audio duration"""
    try:
        logger.info(f"Generating synchronized SRT for: {audio_path}")
        
        # Get actual audio duration
        actual_duration = get_audio_duration(audio_path)
        logger.info(f"Actual audio duration: {actual_duration} seconds")
        
        # Transcribe with Whisper
        result = whisper_model.transcribe(
            audio_path,
            verbose=True,
            condition_on_previous_text=True,
            no_speech_threshold=0.5
        )
        
        # Get original duration from last segment
        original_duration = result["segments"][-1]["end"] if result["segments"] else 0
        logger.info(f"Original Whisper duration: {original_duration} seconds")
        
        # Scale timestamps
        adjusted_segments = scale_timestamps(
            result["segments"],
            actual_duration,
            original_duration
        )
        
        # Generate SRT content
        srt_content = []
        for i, segment in enumerate(adjusted_segments, 1):
            start_time = format_timestamp(segment["start"])
            end_time = format_timestamp(segment["end"])
            
            srt_content.extend([
                str(i),
                f"{start_time} --> {end_time}",
                segment["text"].strip() + "\n",
                ""
            ])
        
        # Save files
        base_path = audio_path.rsplit(".", 1)[0]
        srt_path = f"{base_path}.srt"
        
        with open(srt_path, "w", encoding="utf-8") as f:
            f.write("\n".join(srt_content))
        
        # Save metadata
        metadata = {
            **(segment_info or {}),
            "actual_duration": actual_duration,
            "original_duration": original_duration,
            "scale_factor": actual_duration / original_duration if original_duration else 1,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        metadata_path = f"{base_path}.json"
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Successfully generated synchronized SRT: {srt_path}")
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
def infer(ref_audio_orig, ref_text, gen_text, remove_silence=False, cross_fade_duration=0.15, speed=1.0):
    """Generate audio using F5-TTS model"""
    logger.info("Starting text preprocessing...")
    gen_text = gen_text.lower()
    gen_text = translate_number_to_text(gen_text)
    
    # Inference process
    final_wave, final_sample_rate, combined_spectrogram = infer_process(
        ref_audio_orig, ref_text, gen_text, F5TTS_ema_model, vocoder,
        cross_fade_duration=cross_fade_duration, speed=speed
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
        
        # Generate synchronized SRT
        if segment_index is not None:
            segment_info = {
                "segment_index": segment_index,
                "original_text": gen_text,
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
        total_duration = 0
        
        for path in file_paths:
            if not os.path.exists(path):
                raise HTTPException(status_code=404, detail=f"Audio file not found: {path}")
            
            segment = AudioSegment.from_wav(path)
            combined += segment
            total_duration += len(segment) / 1000.0
        
        output_path = os.path.join("/app/generated_audio_files", f"combined_{int(time.time())}.wav")
        combined.export(output_path, format="wav")
        
        logger.info(f"Combined audio duration: {total_duration} seconds")
        return {
            "status": "success",
            "filename": os.path.basename(output_path),
            "full_path": output_path,
            "total_duration": total_duration
        }
    
    except Exception as e:
        logger.error(f"Error combining audio segments: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    

@app.post("/generate-combined-srt/")
async def generate_combined_srt(file_paths: List[str]):
    """Generate combined SRT file from multiple audio segments with improved error handling"""
    try:
        logger.info(f"Starting combined SRT generation for {len(file_paths)} files")
        
        # Validate input paths
        for path in file_paths:
            if not os.path.exists(path):
                raise HTTPException(
                    status_code=404,
                    detail=f"Audio file not found: {path}"
                )
        
        all_segments = []
        current_index = 1
        time_offset = 0.0
        gap_duration = 0.05  # 50ms gap
        
        # Calculate total duration
        total_duration = 0
        segment_durations = []
        
        for path in file_paths:
            try:
                duration = get_audio_duration(path)
                segment_durations.append(duration)
                total_duration += duration
                logger.info(f"Duration for {path}: {duration}s")
            except Exception as e:
                logger.error(f"Error getting duration for {path}: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to process audio file: {str(e)}"
                )
        
        # Add gaps between segments
        total_duration += gap_duration * (len(file_paths) - 1)
        logger.info(f"Total duration with gaps: {total_duration}s")
        
        for i, path in enumerate(file_paths):
            try:
                # Generate individual SRT with proper error handling
                srt_path = generate_synchronized_srt(
                    path,
                    {
                        "offset": time_offset,
                        "segment_index": i,
                        "duration": segment_durations[i]
                    }
                )
                
                if not os.path.exists(srt_path):
                    raise Exception(f"SRT file not generated for segment {i}")
                
                # Read and process SRT content
                with open(srt_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                
                current_segment = []
                for line in lines:
                    line = line.strip()
                    if line.isdigit():
                        if current_segment:
                            all_segments.append(current_segment)
                        current_segment = [str(current_index)]
                        current_index += 1
                    elif " --> " in line:
                        try:
                            start, end = line.split(" --> ")
                            # Convert timestamps with error handling
                            start_time = timedelta(
                                hours=int(start[:2]),
                                minutes=int(start[3:5]),
                                seconds=float(start[6:].replace(",", "."))
                            ).total_seconds() + time_offset
                            
                            end_time = timedelta(
                                hours=int(end[:2]),
                                minutes=int(end[3:5]),
                                seconds=float(end[6:].replace(",", "."))
                            ).total_seconds() + time_offset
                            
                            current_segment.append(
                                f"{format_timestamp(start_time)} --> {format_timestamp(end_time)}"
                            )
                        except ValueError as e:
                            logger.error(f"Error parsing timestamp: {str(e)}")
                            continue
                    elif line:
                        current_segment.append(line)
                
                if current_segment:
                    all_segments.append(current_segment)
                
                # Update offset for next segment
                time_offset += segment_durations[i]
                if i < len(file_paths) - 1:  # Don't add gap after last segment
                    time_offset += gap_duration
                
                logger.info(f"Processed segment {i + 1}/{len(file_paths)}")
                
            except Exception as e:
                logger.error(f"Error processing segment {i}: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Error processing segment {i + 1}: {str(e)}"
                )
        
        if not all_segments:
            raise HTTPException(
                status_code=500,
                detail="No segments were successfully processed"
            )
        
        # Generate output path
        output_dir = "/app/generated_audio_files"
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"combined_{int(time.time())}.srt")
        
        # Write combined SRT
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                for segment in all_segments:
                    f.write("\n".join(segment))
                    f.write("\n\n")
        except Exception as e:
            logger.error(f"Error writing combined SRT: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to write combined SRT: {str(e)}"
            )
        
        logger.info(f"Successfully generated combined SRT: {output_path}")
        
        return FileResponse(
            path=output_path,
            filename=os.path.basename(output_path),
            media_type="application/x-subrip"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in generate_combined_srt: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate combined SRT: {str(e)}"
        )