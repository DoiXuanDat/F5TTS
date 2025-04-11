import logging
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi import APIRouter

from pathlib import Path
import json
import os

from config import AUDIO_DIR
from api.middleware import setup_middleware
from api.routes import audio, video, srt, kokoro, transcription
from services.video_service import video_storage
from ngrok_config import NgrokManager

# Configure custom logging format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)
router = APIRouter()

# Define base directories
BASE_DIR = Path(__file__).parent
STATIC_DIR = BASE_DIR / "static"
if not STATIC_DIR.exists():
    STATIC_DIR.mkdir(parents=True)

# Config file for client configuration
CONFIG_FILE = STATIC_DIR / "config.json"

# Initialize FastAPI app
app = FastAPI(title="F5 TTS API", description="API for text-to-speech conversion using F5 TTS model")

# Setup CORS to allow all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
    expose_headers=["Content-Disposition"]
)

# Setup additional middleware
setup_middleware(app)

# Ensure directories exist
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
app.include_router(transcription.router, tags=["Audio Transcription"])

# Initialize video storage
video_storage.load_videos()

# Serve frontend routes for SPA
@app.get("/")
async def root():
    """API root endpoint - serve frontend"""
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    
    # Fallback to API info if frontend not found
    return {
        "message": "F5 TTS API is running",
        "endpoints": {
            "audio": "/generate-audio/",
            "combine_audio": "/combine-audio",
            "video_management": "/videos/",
            "srt_generation": "/generate-combined-srt",
            "kokoro_tts": "/generate-audio-kokoro/",
            "transcription": "/transcribe-audio/"
        }
    }

@app.get("/api/config")
async def get_config():
    """Return the configuration including ngrok URL to the client"""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r') as f:
                return JSONResponse(json.load(f))
        except Exception as e:
            logger.error(f"Error reading config file: {e}")
    
    # Return default config if file doesn't exist
    return JSONResponse({
        "apiBaseUrl": f"http://localhost:8000",
        "timestamp": None
    })

@app.middleware("http")
async def log_requests(request, call_next):
    print(f"Request path: {request.url.path}")
    response = await call_next(request)
    return response

@app.get("/videos/")
async def get_videos_debug():
    return [{"id": "debug1", "title": "Debug Video", "status": "completed"}]

@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    # Nếu path bắt đầu bằng api/ hoặc là các API endpoints đã biết, trả về 404
    if full_path.startswith(("api/", "audio/")) or full_path == "videos/":
        raise HTTPException(status_code=404, detail="API endpoint not found")
    
    # Phục vụ frontend cho tất cả các đường dẫn khác
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    else:
        raise HTTPException(status_code=404, detail="Frontend not found")


if __name__ == "__main__":
    import uvicorn
    
    # Start ngrok and get public URL
    ngrok_manager = NgrokManager()
    try:
        public_url = ngrok_manager.start(port=8000)
        print(f"\n🌐 Your app is publicly accessible at: {public_url}")
        
        # For people sharing the app, add instructions for viewers
        print(f"\n📱 To let others use your app:")
        print(f"   1. Share this URL: {public_url}")
        print(f"   2. When they first open the app, they need to click the '⚙️ API Config' button")
        print(f"   3. They should set the API URL to: {public_url}")
        print(f"   4. Then click 'Test Connection' to verify it works")
        print(f"   5. Click 'Save' and they're ready to use your app!")
    except Exception as e:
        print(f"\n⚠️ Failed to start ngrok: {e}")
        print(f"The app will still run locally at http://localhost:8000")
    
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8000,
        reload=False,  # Set to False when using ngrok
        access_log=True,
        log_config=None
    )