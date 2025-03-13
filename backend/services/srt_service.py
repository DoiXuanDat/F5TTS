import os
import json
from config import AUDIO_DIR, logger
from utils.audio import get_audio_duration, format_timestamp

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
            "timestamp": segment_info.get("timestamp", "")
        }
        
        metadata_path = f"{base_path}.json"
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)
        
        return srt_path
    except Exception as e:
        logger.error(f"Error generating synchronized SRT: {str(e)}", exc_info=True)
        raise Exception(f"Failed to generate synchronized SRT: {str(e)}")

def generate_combined_srt_content(audio_paths):
    """Generate SRT content for multiple audio segments"""
    srt_entries = []
    
    for path in audio_paths:
        full_path = AUDIO_DIR / path
        metadata_path = str(full_path).rsplit(".", 1)[0] + ".json"
        
        if not os.path.exists(metadata_path):
            logger.error(f"Metadata file not found: {metadata_path}")
            continue
                
        with open(metadata_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)
                
        # Get audio duration for verification
        actual_duration = get_audio_duration(str(full_path))
        
        srt_entries.append({
            "index": metadata.get("segment_index", len(srt_entries) + 1),
            "start_time": format_timestamp(0),
            "end_time": format_timestamp(actual_duration),
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

    return "\n".join(srt_content)