// frontend/src/app/services/transcriptionService.js
import axios from 'axios';
import { getBaseURL } from './api';

export const transcriptionService = {
  // Upload and transcribe an audio file
  transcribeAudio: async (audioFile) => {
    try {
      const formData = new FormData();
      formData.append('audio', audioFile);
      
      const response = await axios.post(`${getBaseURL()}/transcribe-audio/`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
      
      return response.data;
    } catch (error) {
      console.error('Transcription error:', error);
      throw new Error(error.response?.data?.message || "Failed to transcribe audio");
    }
  },
  
  // Parse SRT file content
  parseSrtFile: (content) => {
    const regex = /(\d+)\r?\n(\d{2}:\d{2}:\d{2}[,\.]\d{3}) *--> *(\d{2}:\d{2}:\d{2}[,\.]\d{3})[\r\n]+([\s\S]*?)(?=[\r\n]+\d+[\r\n]+\d{2}:\d{2}:\d{2}[,\.]\d{3} *--> *\d{2}:\d{2}:\d{2}[,\.]\d{3}|$)/g;
    
    const subtitles = [];
    let match;
    
    while ((match = regex.exec(content)) !== null) {
      const id = Date.now() + '-' + match[1];
      const startTime = match[2].replace(',', '.');
      const endTime = match[3].replace(',', '.');
      
      // Clean up text - remove HTML tags and normalize line breaks
      const text = match[4].trim()
        .replace(/<[^>]*>/g, '')
        .replace(/\r\n|\r|\n/g, ' ')
        .trim();
      
      subtitles.push({
        id,
        text,
        startTime,
        endTime,
        image: null
      });
    }
    
    return subtitles;
  }
};

export default transcriptionService;