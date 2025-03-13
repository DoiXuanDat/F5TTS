import os
import json
from pathlib import Path

def init_video_storage():
    audio_dir = Path(__file__).parent.parent / "generated_audio_files"
    storage_file = audio_dir / "videos.json"
    
    if not audio_dir.exists():
        audio_dir.mkdir(parents=True)
    
    if not storage_file.exists():
        with open(storage_file, 'w', encoding='utf-8') as f:
            json.dump([], f)
        print(f"Initialized empty video storage at {storage_file}")
    else:
        print(f"Video storage already exists at {storage_file}")

if __name__ == "__main__":
    init_video_storage()