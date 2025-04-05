import React, { useState } from 'react';
import PropTypes from 'prop-types';
import axios from 'axios';
import { getBaseURL } from '../../services/api';
import './AudioUploader.css';

const AudioUploader = ({ onTranscriptionComplete, onError }) => {
  const [audioFile, setAudioFile] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [progress, setProgress] = useState(0);

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (!file) return;

    // Validate file type
    const validTypes = ['.wav', '.mp3', 'audio/wav', 'audio/mpeg', 'audio/mp3'];
    const fileType = file.type;
    const extension = file.name.substr(file.name.lastIndexOf('.')).toLowerCase();
    
    if (!validTypes.includes(fileType) && !validTypes.includes(extension)) {
      onError("Please upload a valid audio file (.wav or .mp3)");
      return;
    }

    setAudioFile(file);
  };

  const handleTranscribeAudio = async () => {
    if (!audioFile) {
      onError("Please select an audio file first");
      return;
    }

    setIsLoading(true);
    setProgress(10);

    const formData = new FormData();
    formData.append('audio', audioFile);

    try {
      // Since we don't have a transcription endpoint yet, we'll simulate one
      // In a real implementation, you would call your backend API
      setProgress(30);
      
      // TODO: Replace with actual API call when backend is ready
      const response = await axios.post(`${getBaseURL()}/transcribe-audio/`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        },
        onUploadProgress: (progressEvent) => {
          const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          setProgress(percentCompleted > 90 ? 90 : percentCompleted);
        }
      });

      setProgress(100);
      
      // Call the parent component with the transcribed text
      if (response.data && response.data.text) {
        onTranscriptionComplete(response.data.text);
      } else {
        // Fallback for testing until API is implemented
        // Remove this in production
        setTimeout(() => {
          const mockText = "This is a simulated transcription. Replace this with the actual API call when ready.";
          onTranscriptionComplete(mockText);
          setIsLoading(false);
        }, 2000);
      }
    } catch (error) {
      console.error('Transcription error:', error);
      
      // For now, let's use a mock response for testing
      // Remove this in production
      setTimeout(() => {
        const mockText = "This is a simulated transcription. The actual API is not yet implemented.";
        onTranscriptionComplete(mockText);
        setIsLoading(false);
      }, 2000);
      
      // Uncomment this when the API is ready
      // onError(error.response?.data?.message || "Failed to transcribe audio");
      // setIsLoading(false);
    }
  };

  return (
    <div className="audio-uploader">
      <div className="upload-container">
        <input
          type="file"
          id="audio-file"
          accept=".wav,.mp3,audio/wav,audio/mpeg"
          onChange={handleFileChange}
          className="file-input"
        />
        <label htmlFor="audio-file" className="file-label">
          {audioFile ? audioFile.name : "Choose Audio File (.wav or .mp3)"}
        </label>
        
        <button 
          className="transcribe-button"
          onClick={handleTranscribeAudio}
          disabled={!audioFile || isLoading}
        >
          {isLoading ? "Transcribing..." : "Transcribe Audio"}
        </button>
      </div>
      
      {isLoading && (
        <div className="progress-container">
          <div className="progress-bar">
            <div 
              className="progress-fill" 
              style={{ width: `${progress}%` }}
            ></div>
          </div>
          <div className="progress-text">{progress}% Complete</div>
        </div>
      )}
      
      <div className="upload-info">
        <p>Upload an audio file to automatically transcribe it to text and create subtitles.</p>
      </div>
    </div>
  );
};

AudioUploader.propTypes = {
  onTranscriptionComplete: PropTypes.func.isRequired,
  onError: PropTypes.func.isRequired
};

export default AudioUploader;