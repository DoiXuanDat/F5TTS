# backend/config.py
import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Define base directory for audio files
BASE_DIR = Path(__file__).parent
PROJECT_DIR = BASE_DIR.parent
AUDIO_DIR = BASE_DIR / "generated_audio_files"
KOKORO_DIR = PROJECT_DIR / "kokoro-tts"  # Update Kokoro path
if not AUDIO_DIR.exists():
    AUDIO_DIR.mkdir(parents=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

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