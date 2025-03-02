import axios from 'axios';

export const BASE_URL = 'http://localhost:8000'; // Match FastAPI default port

export const audioService = {
  generateAudio: async (formData) => {
    try {
      const response = await axios.post(`${BASE_URL}/generate-audio`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        },
        withCredentials: true,
        maxRedirects: 5
      });
      return response.data;
    } catch (error) {
      console.error('Error generating audio:', error);
      throw error;
    }
  }
};

export const combineAudioSegments = async (paths) => {
    try {
        const response = await axios.post(`${BASE_URL}/combine-audio`, {
            paths: paths  // Make sure paths is wrapped in an object
        }, {
            headers: {
                'Content-Type': 'application/json'
            },
            withCredentials: true
        });
        return response.data;
    } catch (error) {
        console.error('Error combining audio:', error);
        throw handleApiError(error);
    }
};

export const generateSRT = async (audioPath) => {
    try {
        const response = await axios.post(`${BASE_URL}/generate-srt`, 
            { audioPath },
            { responseType: 'blob' }
        );
        return response.data;
    } catch (error) {
        throw handleApiError(error);
    }
};

export const generateCombinedSRT = async (audioPaths) => {
    try {
      const response = await axios.post(
        `${BASE_URL}/generate-combined-srt`,
        { audio_paths: audioPaths },
        {
          headers: { 'Content-Type': 'application/json' },
          responseType: 'text' 
        }
      );

      if (response.status === 200) {
        return response;
      } else {
        throw new Error(`Server returned status ${response.status}`);
      }
    } catch (error) {
      console.error('Error generating combined SRT:', error);
      throw error;
    }
  };

export const generateAllSRT = async (paths) => {
    try {
        const response = await axios.post(`${BASE_URL}/generate-all-srt`, 
            { paths },
            { responseType: 'blob' }
        );
        return response.data;
    } catch (error) {
        throw handleApiError(error);
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