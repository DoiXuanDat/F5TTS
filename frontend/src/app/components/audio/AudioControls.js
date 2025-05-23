// frontend/src/app/components/audio/AudioControls.js
import React, { useState, useRef, useEffect } from 'react';
import PropTypes from 'prop-types';
import { getBaseURL } from '../../services/api';
import './AudioControls.css';

const AudioControls = ({ audioUrl, label, isLoading }) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [duration, setDuration] = useState(0);
  const audioRef = useRef(null);

  useEffect(() => {
    // Tải metadata âm thanh để lấy thời lượng thực tế
    const audio = audioRef.current;
    if (audio) {
      audio.addEventListener('loadedmetadata', () => {
        setDuration(audio.duration);
      });
    }
  }, [audioUrl]);

  const handlePlayPause = () => {
    if (audioRef.current) {
      if (isPlaying) {
        audioRef.current.pause();
      } else {
        audioRef.current.play();
      }
      setIsPlaying(!isPlaying);
    }
  };

  const getAudioSource = () => {
    // Đảm bảo URL âm thanh có định dạng đúng
    if (audioUrl.startsWith('http')) {
      return audioUrl; // Nếu đã là URL đầy đủ
    }
    
    // Nếu URL được lưu trữ trong localStorage, sử dụng nó
    const baseUrl = getBaseURL();
    
    // Nếu baseUrl không rỗng, sử dụng nó
    if (baseUrl) {
      return `${baseUrl}/${audioUrl}`;
    }
    
    // Nếu không, sử dụng đường dẫn tương đối
    return `/${audioUrl}`;
  };

  const handleDownload = async () => {
    try {
      const response = await fetch(getAudioSource());
      if (!response.ok) throw new Error('Download failed');
      
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.style.display = 'none';
      a.href = url;
      a.download = label ? `${label}.wav` : 'audio.wav';
      
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error('Error downloading audio:', error);
    }
  };

  const handleAudioEnd = () => {
    setIsPlaying(false);
  };

  return (
    <div className="audio-controls">
      <div className="audio-player">
        {isLoading ? (
          <div className="loading">Generating audio...</div>
        ) : (
          <audio 
            ref={audioRef} 
            src={getAudioSource()}
            onEnded={handleAudioEnd}
            controls
            preload="metadata"
          />
        )}
        {duration > 0 && (
          <div className="duration-info">
            Duration: {Math.floor(duration)}s
          </div>
        )}
      </div>
      <div className="audio-buttons">
        <button 
          onClick={handlePlayPause}
          disabled={isLoading}
        >
          {isPlaying ? 'Pause' : 'Play'}
        </button>
        <button 
          onClick={handleDownload}
          disabled={isLoading}
        >
          Download {label || 'Audio'}
        </button>
      </div>
    </div>
  );
};

AudioControls.propTypes = {
  audioUrl: PropTypes.string.isRequired,
  label: PropTypes.string,
  isLoading: PropTypes.bool
};

AudioControls.defaultProps = {
  isLoading: false
};

export default AudioControls;