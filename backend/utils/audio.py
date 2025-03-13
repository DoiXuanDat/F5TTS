import os
import tempfile
from pydub import AudioSegment
import soundfile as sf
import torchaudio

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
    from config import logger
    
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

def save_audio_file(audio_data, sample_rate, output_path):
    """Save audio data to a WAV file"""
    import numpy as np
    
    if isinstance(audio_data, np.ndarray):
        sf.write(str(output_path), audio_data, sample_rate)
        return True
    else:
        raise ValueError("Invalid audio data format")