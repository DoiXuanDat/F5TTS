import React, { useState, useRef, useEffect } from 'react';
import PropTypes from 'prop-types';
import { BASE_URL } from '../../services/api';
import { createDownloadLink } from '../../services/audioProcessing';
import './AudioControls.css';

const AudioControls = ({ audioUrl, label }) => {
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

  const handleDownload = async () => {
    try {
      const response = await fetch(`${BASE_URL}/${audioUrl}`);
      const blob = await response.blob();
      const filename = `${label || 'audio'}.wav`;
      
      const link = document.createElement('a');
      link.href = URL.createObjectURL(blob);
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(link.href);
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
        <audio 
          ref={audioRef} 
          src={`${BASE_URL}/${audioUrl}`}
          onEnded={handleAudioEnd}
          controls
          preload="metadata"  // Add this to load duration info
        />
        {duration > 0 && (
          <div className="duration-info">
            Duration: {Math.floor(duration)}s
          </div>
        )}
      </div>
      <div className="audio-buttons">
        <button onClick={handlePlayPause}>
          {isPlaying ? 'Pause' : 'Play'}
        </button>
        <button onClick={handleDownload}>
          Download {label || 'Audio'}
        </button>
      </div>
    </div>
  );
};

AudioControls.propTypes = {
  audioUrl: PropTypes.string.isRequired,
  label: PropTypes.string
};

export default AudioControls;