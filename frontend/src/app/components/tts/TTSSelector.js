// frontend/src/app/components/tts/TTSSelector.js
import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import axios from 'axios';
import { getBaseURL } from '../../services/api';
import './TTSSelector.css';

const TTSSelector = ({ onProviderChange, selectedProvider, disabled }) => {
  const [minimaxVoices, setMinimaxVoices] = useState([]);
  const [kokoroSpeakers, setKokoroSpeakers] = useState([]);
  const [selectedVoice, setSelectedVoice] = useState('female-voice-1');
  const [selectedSpeaker, setSelectedSpeaker] = useState('default');
  const [loading, setLoading] = useState(false);
  
  // Fetch voices/speakers when provider changes
  useEffect(() => {
    if (selectedProvider === 'minimax') {
      fetchMinimaxVoices();
    } else if (selectedProvider === 'kokoro') {
      fetchKokoroSpeakers();
    }
  }, [selectedProvider]);
  
  const fetchMinimaxVoices = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${getBaseURL()}/minimax-voices/`);
      if (response.data && Array.isArray(response.data)) {
        setMinimaxVoices(response.data);
        if (response.data.length > 0 && !response.data.find(v => v.id === selectedVoice)) {
          setSelectedVoice(response.data[0].id);
          onProviderChange('minimax', response.data[0].id);
        }
      }
    } catch (error) {
      console.error('Error fetching MiniMax voices:', error);
    } finally {
      setLoading(false);
    }
  };
  
  const fetchKokoroSpeakers = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${getBaseURL()}/kokoro-speakers/`);
      if (response.data && Array.isArray(response.data)) {
        setKokoroSpeakers(response.data);
        if (response.data.length > 0 && !response.data.find(s => s.id === selectedSpeaker)) {
          setSelectedSpeaker(response.data[0].id);
          onProviderChange('kokoro', response.data[0].id);
        }
      }
    } catch (error) {
      console.error('Error fetching Kokoro speakers:', error);
    } finally {
      setLoading(false);
    }
  };
  
  const handleProviderChange = (e) => {
    const provider = e.target.value;
    if (provider === 'minimax') {
      onProviderChange(provider, selectedVoice);
    } else if (provider === 'kokoro') {
      onProviderChange(provider, selectedSpeaker);
    } else {
      onProviderChange(provider, null);
    }
  };
  
  const handleVoiceChange = (e) => {
    const voice = e.target.value;
    setSelectedVoice(voice);
    if (selectedProvider === 'minimax') {
      onProviderChange(selectedProvider, voice);
    }
  };
  
  const handleSpeakerChange = (e) => {
    const speaker = e.target.value;
    setSelectedSpeaker(speaker);
    if (selectedProvider === 'kokoro') {
      onProviderChange(selectedProvider, speaker);
    }
  };
  
  return (
    <div className="tts-selector">
      <div className="provider-selector">
        <label htmlFor="tts-provider">TTS Provider:</label>
        <select 
          id="tts-provider" 
          value={selectedProvider}
          onChange={handleProviderChange}
          disabled={disabled}
        >
          <option value="f5-tts">F5-TTS (Local)</option>
          <option value="kokoro">Kokoro-TTS (Local)</option>
          <option value="minimax">MiniMax.io (API)</option>
        </select>
      </div>
      
      {selectedProvider === 'minimax' && (
        <div className="voice-selector">
          <label htmlFor="voice-selection">Voice:</label>
          <select
            id="voice-selection"
            value={selectedVoice}
            onChange={handleVoiceChange}
            disabled={disabled || loading || minimaxVoices.length === 0}
          >
            {minimaxVoices.map(voice => (
              <option key={voice.id} value={voice.id}>{voice.name}</option>
            ))}
          </select>
          {loading && <span className="loading-indicator">Loading voices...</span>}
        </div>
      )}
      
      {selectedProvider === 'kokoro' && (
        <div className="voice-selector">
          <label htmlFor="speaker-selection">Speaker:</label>
          <select
            id="speaker-selection"
            value={selectedSpeaker}
            onChange={handleSpeakerChange}
            disabled={disabled || loading || kokoroSpeakers.length === 0}
          >
            {kokoroSpeakers.map(speaker => (
              <option key={speaker.id} value={speaker.id}>{speaker.name}</option>
            ))}
          </select>
          {loading && <span className="loading-indicator">Loading speakers...</span>}
        </div>
      )}
    </div>
  );
};

TTSSelector.propTypes = {
  onProviderChange: PropTypes.func.isRequired,
  selectedProvider: PropTypes.string.isRequired,
  disabled: PropTypes.bool
};

TTSSelector.defaultProps = {
  disabled: false
};

export default TTSSelector;