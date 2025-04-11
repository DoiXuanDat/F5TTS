// frontend/src/app/services/api.js
import axios from 'axios';

// Default fallback URL if no configuration is found
export const BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';

export const getBaseURL = () => {
  // Priority 1: Use the stored API URL from localStorage
  const storedUrl = localStorage.getItem('api_base_url');
  if (storedUrl) {
    return storedUrl;
  }

  // Priority 2: Auto-detect from current URL (Important for ngrok)
  const currentUrl = window.location.origin;
  if (currentUrl.includes('ngrok')) {
    return currentUrl;
  }

  // Fallback to default
  return 'http://localhost:8000';
};

// Create a single axios instance
const apiClient = axios.create({
  headers: {
    'Content-Type': 'application/json',
  },
});

// Update baseURL on every request to ensure it's always current
apiClient.interceptors.request.use(config => {
  config.baseURL = getBaseURL();
  return config;
});

// Video service functions
export const videoService = {
  getAllVideos: async () => {
    try {
      const response = await apiClient.get('/videos/');
      return response.data;
    } catch (error) {
      console.error('Error fetching videos:', error);
      throw error;
    }
  },
  
  createVideo: async (videoData) => {
    try {
      const response = await apiClient.post('/videos/', videoData);
      return response.data;
    } catch (error) {
      console.error('Error creating video:', error);
      throw error;
    }
  },

  deleteVideo: async (id) => {
    try {
      await apiClient.delete(`/videos/${id}`);
    } catch (error) {
      console.error('Error deleting video:', error);
      throw error;
    }
  }
};

// Audio service functions
export const audioService = {
  generateAudio: async (formData) => {
    const response = await axios.post(`${getBaseURL()}/generate-audio/`, formData);
    return response.data;
  },
  
  getKokoroSpeakers: async () => {
    try {
      const response = await axios.get(`${getBaseURL()}/kokoro-speakers/`);
      return response.data;
    } catch (error) {
      console.error('Error fetching Kokoro speakers:', error);
      throw error;
    }
  },
  
  generateKokoroAudio: async (formData) => {
    try {
      const response = await axios.post(`${getBaseURL()}/generate-audio-kokoro/`, formData);
      return response.data;
    } catch (error) {
      console.error('Error generating Kokoro audio:', error);
      throw error;
    }
  }
};

export default apiClient;

export const combineAudioSegments = async (paths) => {
  try {
    console.log('Sending paths to backend:', paths);
    const response = await axios.post(
      `${getBaseURL()}/combine-audio`, 
      { audio_paths: paths },
      {
        headers: {
          'Content-Type': 'application/json',
        },
      }
    );
    
    console.log('Combine audio response:', response.data);
    return response.data;
  } catch (error) {
    console.error('Error combining audio segments:', error);
    throw new Error(error.response?.data?.detail || 'Failed to combine audio segments');
  }
};

export const generateCombinedSRT = async (paths, paragraphData = []) => {
  try {
    console.log('Generating SRT for paths:', paths);
    
    const response = await axios.post(
      `${getBaseURL()}/generate-combined-srt`,
      { 
        audio_paths: paths,
        paragraph_data: paragraphData
      },
      {
        headers: {
          'Content-Type': 'application/json',
        }
      }
    );
    
    console.log('SRT generation response type:', typeof response.data);
    console.log('SRT generation content-type:', response.headers['content-type']);
    
    // If the response is already text, we can process it here
    if (typeof response.data === 'string') {
      // Replace "None" with sequential numbers
      const lines = response.data.split('\n');
      let subtitleNumber = 1;
      const processedLines = [];
      
      for (let i = 0; i < lines.length; i++) {
        if (lines[i].trim() === 'None') {
          processedLines.push(String(subtitleNumber));
          subtitleNumber++;
        } else {
          processedLines.push(lines[i]);
        }
      }
      
      response.data = processedLines.join('\n');
      return response;
    }
    
    // Otherwise, make a second request with responseType: 'blob'
    const blobResponse = await axios.post(
      `${getBaseURL()}/generate-combined-srt`,
      { 
        audio_paths: paths,
        paragraph_data: paragraphData
      },
      {
        headers: {
          'Content-Type': 'application/json',
        },
        responseType: 'blob'
      }
    );
    
    const blob = blobResponse.data;
    if (blob instanceof Blob) {
      const text = await blob.text();
      const lines = text.split('\n');
      let subtitleNumber = 1;
      const processedLines = [];
      
      for (let i = 0; i < lines.length; i++) {
        if (lines[i].trim() === 'None') {
          processedLines.push(String(subtitleNumber));
          subtitleNumber++;
        } else {
          processedLines.push(lines[i]);
        }
      }
      
      const processedText = processedLines.join('\n');
      const processedBlob = new Blob([processedText], { type: 'text/plain' });
      blobResponse.data = processedBlob;
    }
    
    return blobResponse;
  } catch (error) {
    console.error('Error generating SRT:', error);
    console.error('Error response:', error.response);
    throw new Error(error.response?.data?.detail || 'Failed to generate SRT');
  }
};

export const downloadSRTContent = (content, filename = 'combined.srt') => {
  try {
    let blob;
    
    // If content is already a Blob or File
    if (content instanceof Blob) {
      blob = content;
    } 
    // If content is a string
    else if (typeof content === 'string') {
      blob = new Blob([content], { type: 'text/plain' });
    } 
    // If content is likely JSON or another format
    else {
      // Try to stringify if it's an object
      const textContent = typeof content === 'object' ? JSON.stringify(content) : String(content);
      blob = new Blob([textContent], { type: 'text/plain' });
    }
    
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    
    // Clean up
    setTimeout(() => {
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    }, 100);
    
    return true;
  } catch (error) {
    console.error('Error downloading SRT content:', error);
    return false;
  }
};

export const generateSRT = async (audioPath) => {
  try {
    const response = await axios.post(
      `${getBaseURL()}/generate-srt`,
      { audioPath },
      {
        headers: {
          'Content-Type': 'application/json',
        }
      }
    );
    
    if (typeof response.data === 'string' || response.headers['content-type']?.includes('text/plain')) {
      return response;
    }
    
    return await axios.post(
      `${getBaseURL()}/generate-srt`,
      { audioPath },
      {
        headers: {
          'Content-Type': 'application/json',
        },
        responseType: 'blob'
      }
    );
  } catch (error) {
    console.error('Error generating single SRT:', error);
    throw new Error(error.response?.data?.detail || 'Failed to generate SRT');
  }
};

export const generateAllSRT = async (paths) => {
  try {
    const response = await axios.post(
      `${getBaseURL()}/generate-all-srt`,
      { paths },
      {
        headers: {
          'Content-Type': 'application/json',
        }
      }
    );
    
    if (typeof response.data === 'string' || response.headers['content-type']?.includes('text/plain')) {
      return response;
    }
    
    return await axios.post(
      `${getBaseURL()}/generate-all-srt`,
      { paths },
      {
        headers: {
          'Content-Type': 'application/json',
        },
        responseType: 'blob'
      }
    );
  } catch (error) {
    console.error('Error generating multiple SRTs:', error);
    throw new Error(error.response?.data?.detail || 'Failed to generate SRTs');
  }
};

const handleApiError = (error) => {
    if (error.response) {
        const { data, status } = error.response;
        return {
            message: data.error || 'Server error',
            status,
            timestamp: data.timestamp
        };
    }
    return {
        message: error.message || 'Network error',
        status: 500,
        timestamp: new Date().toISOString()
    };
};