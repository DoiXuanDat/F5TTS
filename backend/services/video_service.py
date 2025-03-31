import json
from datetime import datetime
from typing import Dict, List, Optional
import time
from models.schemas import Video
from config import AUDIO_DIR, logger

class VideoStorage:
    def __init__(self):
        self.storage_file = AUDIO_DIR / "videos.json"
        self.videos: Dict[str, Video] = {}
        self._init_storage()
        self.load_videos()

    def _init_storage(self):
        if not self.storage_file.parent.exists():
            self.storage_file.parent.mkdir(parents=True)
        
        if not self.storage_file.exists():
            with open(self.storage_file, 'w', encoding='utf-8') as f:
                json.dump([], f)

    def load_videos(self):
        try:
            with open(self.storage_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for video_data in data:
                    if 'createdAt' in video_data and video_data['createdAt']:
                        video_data['createdAt'] = datetime.fromisoformat(video_data['createdAt'])
                    video = Video(**video_data)
                    self.videos[video.id] = video
        except json.JSONDecodeError:
            with open(self.storage_file, 'w', encoding='utf-8') as f:
                json.dump([], f)

    def save_videos(self):
        videos_data = [video.dict() for video in self.videos.values()]
        with open(self.storage_file, 'w', encoding='utf-8') as f:
            json.dump(videos_data, f, indent=2, default=self._json_serializer)

    def _json_serializer(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f'Type {type(obj)} not serializable')

    def add_video(self, video: Video) -> Video:
        self.videos[video.id] = video
        self.save_videos()
        return video

    def get_video(self, video_id: str) -> Optional[Video]:
        return self.videos.get(video_id)

    def update_video(self, video_id: str, updates: dict) -> Optional[Video]:
        if video_id not in self.videos:
            return None
        
        video = self.videos[video_id]
        for key, value in updates.items():
            if hasattr(video, key):
                setattr(video, key, value)
                
        self.save_videos()
        return video

    def get_all_videos(self) -> List[Video]:
        return list(self.videos.values())

    def remove_video(self, video_id: str) -> bool:
        if video_id in self.videos:
            del self.videos[video_id]
            self.save_videos()
            return True
        return False

class VideoService:
    def __init__(self):
        self.videos = {}
        
    async def create_video(self, title, audio_path=None):
        video_id = f"VID{int(time.time() * 1000)}"
        self.videos[video_id] = {
            "id": video_id,
            "title": title,
            "status": "pending",  # Add status field
            "audio_path": audio_path,
            "created_at": datetime.now().isoformat()
        }
        return video_id

    def update_video_status(self, video_id, status):
        if video_id in self.videos:
            self.videos[video_id]["status"] = status

video_storage = VideoStorage()
__all__ = ['video_storage']