import os
import json
import time

def save_metadata(filepath, metadata):
    """Save metadata as JSON file"""
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

def load_metadata(filepath):
    """Load metadata from JSON file"""
    if not os.path.exists(filepath):
        return None
    
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

def generate_unique_filename(prefix="generated_audio"):
    """Generate a unique filename based on timestamp"""
    return f"{prefix}_{int(time.time() * 1000)}"