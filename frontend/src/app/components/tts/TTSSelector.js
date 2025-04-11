import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import axios from 'axios';
import { getBaseURL } from '../../services/api';
import './TTSSelector.css';

const TTSSelector = ({ onProviderChange, selectedProvider, disabled }) => {
  const [minimaxVoices, setMinimaxVoices] = useState([]);
  const [kokoroSpeakers, setKokoroSpeakers] = useState([]);
  const [selectedVoice, setSelectedVoice] = useState('female-voice-1');
  const [selectedSpeaker, setSelectedSpeaker] = useState('af_sarah');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  // Fetch voices/speakers when provider changes or component mounts
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
      setError(null);
      console.log('Fetching MiniMax voices...');
      
      // Sử dụng đường dẫn tương đối
      const response = await axios.get(`${getBaseURL()}/minimax-voices/`);
      
      console.log('MiniMax response:', response.data);
      
      if (response.data && Array.isArray(response.data)) {
        setMinimaxVoices(response.data);
        if (response.data.length > 0 && !response.data.find(v => v.id === selectedVoice)) {
          setSelectedVoice(response.data[0].id);
          onProviderChange('minimax', response.data[0].id);
        }
      }
    } catch (error) {
      console.error('Error fetching MiniMax voices:', error);
      setError('Failed to load MiniMax voices');
    } finally {
      setLoading(false);
    }
  };
  
  const fetchKokoroSpeakers = async () => {
    try {
      setLoading(true);
      setError(null);
      console.log('Fetching Kokoro speakers...');
      
      // Sử dụng đường dẫn tương đối
      const response = await axios.get(`${getBaseURL()}/kokoro-speakers/`);
      
      console.log('Kokoro response:', response.data);
      
      if (response.data && Array.isArray(response.data) && response.data.length > 0) {
        setKokoroSpeakers(response.data);
        // Default to first voice if current selection is not in the list
        if (!response.data.find(s => s.id === selectedSpeaker)) {
          const newSpeaker = response.data[0].id;
          setSelectedSpeaker(newSpeaker);
          onProviderChange('kokoro', newSpeaker);
        } else {
          // Ensure the parent component has the correct voice
          onProviderChange('kokoro', selectedSpeaker);
        }
      } else {
        console.warn('Received empty or invalid Kokoro speakers list');
        // Set a default list of voices in case the API fails
        const defaultVoices = [
          { id: 'af_sarah', name: 'Sarah (Female, US)' },
          { id: 'am_adam', name: 'Adam (Male, US)' }
        ];
        setKokoroSpeakers(defaultVoices);
        setSelectedSpeaker(defaultVoices[0].id);
        onProviderChange('kokoro', defaultVoices[0].id);
      }
    } catch (error) {
      console.error('Error fetching Kokoro speakers:', error);
      setError('Failed to load Kokoro speakers');
      
      // Set a default list of voices in case the API fails
      const defaultVoices = [
        { id: 'af_sarah', name: 'Sarah (Female, US)' },
        { id: 'am_adam', name: 'Adam (Male, US)' }
      ];
      setKokoroSpeakers(defaultVoices);
      setSelectedSpeaker(defaultVoices[0].id);
      onProviderChange('kokoro', defaultVoices[0].id);
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
    <div className="tts-selector" data-provider={selectedProvider}>
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
          {error && <span className="error-indicator">{error}</span>}
        </div>
      )}
      
      {selectedProvider === 'kokoro' && (
        <div className="voice-selector">
          <label htmlFor="speaker-selection">Speaker:</label>
          <select
            id="speaker-selection"
            value={selectedSpeaker}
            onChange={handleSpeakerChange}
            disabled={disabled || loading}
          >
            {kokoroSpeakers.length > 0 ? (
              kokoroSpeakers.map(speaker => (
                <option key={speaker.id} value={speaker.id}>{speaker.name}</option>
              ))
            ) : (
              <option value="af_sarah">Sarah (Default)</option>
            )}
          </select>
          {loading && <span className="loading-indicator">Loading speakers...</span>}
          {error && <span className="error-indicator">{error}</span>}
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