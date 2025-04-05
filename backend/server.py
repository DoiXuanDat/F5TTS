import logging
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from starlette.responses import RedirectResponse
import json

from config import AUDIO_DIR
from api.middleware import setup_middleware
from api.routes import audio, video, srt, kokoro, transcription  # Add transcription import
from services.video_service import video_storage
from ngrok_config import NgrokManager

# Configure custom logging format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Define base directories
BASE_DIR = Path(__file__).parent
STATIC_DIR = BASE_DIR / "static"
if not STATIC_DIR.exists():
    STATIC_DIR.mkdir(parents=True)

# Initialize FastAPI app
app = FastAPI(title="F5 TTS API", description="API for text-to-speech conversion using F5 TTS model")

# Setup middleware (CORS, etc.)
setup_middleware(app)

# Ensure audio directory exists
if not AUDIO_DIR.exists():
    AUDIO_DIR.mkdir(parents=True)

# Mount static files directories
app.mount("/audio", StaticFiles(directory=str(AUDIO_DIR)), name="audio")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Include routers from different modules
app.include_router(audio.router, tags=["Audio Generation"])
app.include_router(video.router, tags=["Video Management"])
app.include_router(srt.router, tags=["SRT Generation"])
app.include_router(kokoro.router, tags=["Kokoro TTS"])
app.include_router(transcription.router, tags=["Audio Transcription"])  # Add transcription router

# Initialize video storage
video_storage.load_videos()

@app.get("/")
async def root():
    """API root endpoint - serve backend info or redirect to frontend"""
    # Check if we're serving the frontend
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    
    # Otherwise return API info
    return {
        "message": "F5 TTS API is running",
        "endpoints": {
            "audio": "/generate-audio/",
            "combine_audio": "/combine-audio",
            "video_management": "/videos/",
            "srt_generation": "/generate-combined-srt",
            "kokoro_tts": "/generate-audio-kokoro/",
            "transcription": "/transcribe-audio/"  # Add transcription endpoint
        }
    }

# Serve frontend routes for SPA
@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    # If path starts with api/ or known API endpoints, raise 404
    if full_path.startswith(("api/", "audio/", "videos/")):
        raise HTTPException(status_code=404, detail="API endpoint not found")
    
    # Otherwise, serve the frontend index.html
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    else:
        raise HTTPException(status_code=404, detail="Frontend not found")
    

if __name__ == "__main__":
    import uvicorn
    
    # Khởi động ngrok và lấy URL công khai
    ngrok_manager = NgrokManager()
    public_url = ngrok_manager.start(port=8000)
    print(f"\n🌐 Your app is publicly accessible at: {public_url}")
    
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        access_log=True,
        log_config=None
    )