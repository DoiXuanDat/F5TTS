# backend/services/minimax_tts_service.py
import requests
import json
import os
import logging
from config import logger

class MinimaxTTSService:
    def __init__(self):
        self.api_key = os.environ.get("MINIMAX_API_KEY", "")
        self.group_id = os.environ.get("MINIMAX_GROUP_ID", "")
        self.base_url = "https://api.minimax.chat/v1/text_to_speech"
        
    def generate_speech(self, text, voice_id="female-voice-1", speed=1.0):
        """Generate speech using MiniMax TTS API"""
        if not self.api_key or not self.group_id:
            raise ValueError("MiniMax API credentials not configured")
            
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        payload = {
            "text": text,
            "model_name": "speech-01",
            "voice_id": voice_id,
            "speed": speed,
            "group_id": self.group_id
        }
        
        try:
            logger.info(f"Sending request to MiniMax TTS API: {text[:50]}...")
            response = requests.post(self.base_url, headers=headers, json=payload)
            
            if response.status_code != 200:
                logger.error(f"MiniMax API error: {response.status_code}, {response.text}")
                raise Exception(f"MiniMax API error: {response.status_code}")
                
            result = response.json()
            if "audio_data" not in result:
                logger.error(f"MiniMax API unexpected response: {result}")
                raise Exception("MiniMax API returned unexpected response")
                
            return result["audio_data"], 24000  # Return audio data and sample rate
            
        except Exception as e:
            logger.error(f"Error in MiniMax TTS service: {str(e)}")
            raise
            
    def get_available_voices(self):
        """Get list of available voices from MiniMax API"""
        # Replace with actual API call if MiniMax provides voice listing endpoint
        return [
            {"id": "female-voice-1", "name": "Female Voice 1"},
            {"id": "male-voice-1", "name": "Male Voice 1"},
            # Add more voices as they become available
        ]

# Instantiate the service
minimax_tts_service = MinimaxTTSService()