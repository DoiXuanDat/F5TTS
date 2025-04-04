# backend/api/routes/srt.py
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response, PlainTextResponse
from pydantic import BaseModel
from typing import List
import json
import traceback

from models.schemas import SRTRequest
from services.srt_service import generate_combined_srt_content
from config import logger

router = APIRouter()

@router.post("/generate-combined-srt")
async def generate_combined_srt(request: SRTRequest):
    """
    Generate a combined SRT file for multiple audio segments
    Returns the SRT content as plain text
    """
    try:
        logger.info(f"Received SRT request with {len(request.audio_paths)} audio paths")
        logger.info(f"Audio paths: {request.audio_paths}")
        
        # Generate the SRT content
        srt_text = generate_combined_srt_content(request.audio_paths)
        
        logger.info(f"Successfully generated SRT content ({len(srt_text)} bytes)")
        
        # Return as plain text with appropriate headers for download
        return Response(
            content=srt_text,
            media_type="text/plain",
            headers={
                "Content-Disposition": "attachment; filename=combined.srt",
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )

    except Exception as e:
        logger.error(f"Error generating SRT: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate SRT: {str(e)}"
        )