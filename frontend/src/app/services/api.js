import axios from 'axios';

export const BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';

export const getBaseURL = () => BASE_URL;

// Tạo phiên bản axios duy nhất
const apiClient = axios.create({
  baseURL: getBaseURL(),
  headers: {
    'Content-Type': 'application/json',
  },
});

// Cập nhật baseURL nếu được lưu trữ trong localStorage
apiClient.interceptors.request.use(config => {
  config.baseURL = getBaseURL();
  return config;
});

// Các hàm dịch vụ video
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

// Các hàm dịch vụ âm thanh
export const audioService = {
  generateAudio: async (formData) => {
    const response = await axios.post(`${BASE_URL}/generate-audio/`, formData);
    return response.data;
  },
  
  getKokoroVoices: async () => {
    const response = await axios.get(`${BASE_URL}/kokoro-voices/`);
    return response.data;
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
    
    // Ghi nhật ký phản hồi để gỡ lỗi
    console.log('Combine audio response:', response.data);
    return response.data;
  } catch (error) {
    console.error('Error combining audio segments:', error);
    throw new Error(error.response?.data?.detail || 'Failed to combine audio segments');
  }
};

export const generateSRT = async (audioPath) => {
    try {
        const response = await axios.post(`${getBaseURL()}/generate-srt`, 
            { audioPath },
            { responseType: 'blob' }
        );
        return response.data;
    } catch (error) {
        throw handleApiError(error);
    }
};

export const generateCombinedSRT = async (paths) => {
  try {
    const response = await axios.post(
      `${getBaseURL()}/generate-combined-srt`,
      { audio_paths: paths },
      {
        headers: {
          'Content-Type': 'application/json',
        },
        responseType: 'blob',
      }
    );
    return response;
  } catch (error) {
    console.error('Error generating SRT:', error);
    throw new Error(error.response?.data?.detail || 'Failed to generate SRT');
  }
};

export const generateAllSRT = async (paths) => {
    try {
        const response = await axios.post(`${getBaseURL()}/generate-all-srt`, 
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
