from fastapi import APIRouter, HTTPException
from typing import List
from datetime import datetime
import logging

from models.schemas import VideoCreate, VideoUpdate, Video
from services.video_service import video_storage

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

@router.get("/videos/", response_model=List[Video])
async def list_videos():
    """Get all videos from storage"""
    try:
        videos = video_storage.get_all_videos()
        logger.info(f"Retrieved {len(videos)} videos")
        return videos
    except Exception as e:
        logger.error(f"Error retrieving videos: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/videos/", response_model=Video)
async def create_video(video: VideoCreate):
    """Create a new video entry"""
    try:
        video_id = f"VID{int(datetime.now().timestamp() * 1000)}"
        new_video = Video(
            id=video_id,
            title=video.title,
            status="pending",
            createdAt=datetime.now(),
            url=video.audioPath,
            metadata={"srtPath": video.srtPath} if video.srtPath else None
        )
        stored_video = video_storage.add_video(new_video)
        logger.info(f"Created new video with ID: {video_id}")
        return stored_video
    except Exception as e:
        logger.error(f"Error creating video: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/videos/{video_id}", response_model=Video)
async def get_video(video_id: str):
    """Get a specific video by ID"""
    try:
        video = video_storage.get_video(video_id)
        if not video:
            raise HTTPException(status_code=404, detail="Video not found")
        return video
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting video: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/videos/{video_id}", response_model=Video)
async def update_video(video_id: str, video_update: VideoUpdate):
    """Update a video's information"""
    try:
        updated_video = video_storage.update_video(video_id, video_update.dict(exclude_unset=True))
        if not updated_video:
            raise HTTPException(status_code=404, detail="Video not found")
        return updated_video
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating video: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/videos/{video_id}")
async def delete_video(video_id: str):
    """Delete a video from storage"""
    try:
        if video_storage.remove_video(video_id):
            return {"status": "success", "message": "Video deleted successfully"}
        raise HTTPException(status_code=404, detail="Video not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting video: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))