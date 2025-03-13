from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from models.schemas import SRTRequest
from services.srt_service import generate_combined_srt_content
from config import logger

router = APIRouter()

@router.post("/generate-combined-srt")
async def generate_combined_srt(request: SRTRequest):
    try:
        logger.info(f"Received request with paths: {request.audio_paths}")
        
        srt_text = generate_combined_srt_content(request.audio_paths)
        
        return Response(
            content=srt_text,
            media_type="text/plain",
            headers={
                "Content-Disposition": "attachment; filename=combined.srt"
            }
        )

    except Exception as e:
        logger.error(f"Error generating SRT: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate SRT: {str(e)}"
        )
