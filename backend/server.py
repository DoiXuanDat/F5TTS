import logging
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from config import AUDIO_DIR
from api.middleware import setup_middleware
from api.routes import audio, video, srt
from services.video_service import video_storage

# Configure custom logging format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Initialize FastAPI app
app = FastAPI(title="F5 TTS API", description="API for text-to-speech conversion using F5 TTS model")

# Setup middleware (CORS, etc.)
setup_middleware(app)

# Ensure audio directory exists
if not AUDIO_DIR.exists():
    AUDIO_DIR.mkdir(parents=True)

# Mount static files directory for serving audio files
app.mount("/audio", StaticFiles(directory=str(AUDIO_DIR)), name="audio")

# Include routers from different modules
app.include_router(audio.router, tags=["Audio Generation"])
app.include_router(video.router, tags=["Video Management"])
app.include_router(srt.router, tags=["SRT Generation"])

# Initialize video storage
video_storage.load_videos()

@app.get("/")
async def root():
    return {
        "message": "F5 TTS API is running",
        "endpoints": {
            "audio": "/generate-audio/",
            "combine_audio": "/combine-audio",
            "video_management": "/videos/",
            "srt_generation": "/generate-combined-srt"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        access_log=True,
        log_config=None  # Use our custom logging config
    )