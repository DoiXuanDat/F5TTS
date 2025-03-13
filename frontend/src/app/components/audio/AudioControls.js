import React, { useState, useRef, useEffect } from 'react';
import PropTypes from 'prop-types';
import { BASE_URL } from '../../services/api';
// import { createDownloadLink } from '../../services/audioProcessing';
import './AudioControls.css';

const AudioControls = ({ audioUrl, label, isLoading }) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [duration, setDuration] = useState(0);
  const audioRef = useRef(null);

  useEffect(() => {
    // Load audio metadata to get actual duration
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

  const getAudioSource = () => `${BASE_URL}/${audioUrl}`;

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
            src={`${BASE_URL}/${audioUrl}`}
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