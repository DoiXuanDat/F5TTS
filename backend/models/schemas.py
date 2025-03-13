from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict
from pydantic import BaseModel

class VideoStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"

class VideoCreate(BaseModel):
    title: str
    audioPath: str
    srtPath: Optional[str] = None

class Video(BaseModel):
    id: str
    title: str
    status: str = 'pending'
    createdAt: datetime = None
    url: Optional[str] = None
    error: Optional[str] = None
    metadata: Optional[dict] = None

    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }

class VideoUpdate(BaseModel):
    status: Optional[VideoStatus] = None
    error: Optional[str] = None
    url: Optional[str] = None

class AudioPaths(BaseModel):
    paths: List[str]

class CombineAudioRequest(BaseModel):
    audio_paths: List[str]

class SRTRequest(BaseModel):
    audio_paths: List[str]