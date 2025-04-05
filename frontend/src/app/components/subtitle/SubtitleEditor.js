// frontend/src/app/components/subtitle/SubtitleEditor.js

import React, { useState, useEffect, useCallback, useMemo } from "react";
import PropTypes from "prop-types";
import axios from 'axios';
import { getBaseURL } from '../../services/api';
import { VideoStatus } from '../../types/video';
import FilePicker from "../common/filePicker/FilePicker";
import SubtitleList from "./SubtitleList";
import TTSSelector from '../tts/TTSSelector';
import AudioControls from "../audio/AudioControls";
import {
  audioService,
  combineAudioSegments,
  generateCombinedSRT,
  downloadSRTContent 
} from "../../services/api";
import "./SubtitleEditor.css";

const DEFAULT_IMAGES = [
  require("../../assets/images/30.png"),
  require("../../assets/images/31.png"),
  require("../../assets/images/32.png"),
  require("../../assets/images/33.png"),
];

// Utility function to split text into paragraphs by double line breaks
const splitTextIntoParagraphs = (text) => {
  return text.split('\n\n').filter(paragraph => paragraph.trim());
};

const SubtitleEditor = ({
  subtitleSegments,
  onSegmentsUpdate,
  setIsProcessing: setParentIsProcessing,
  onGenerationComplete
}) => {
  const [ttsProvider, setTtsProvider] = useState('f5-tts');
  const [voiceOrSpeaker, setVoiceOrSpeaker] = useState(null);

  const handleProviderChange = (provider, voiceOrSpeakerId) => {
    setTtsProvider(provider);
    setVoiceOrSpeaker(voiceOrSpeakerId);
  };

  const [editorState, setEditorState] = useState({
    subtitles: subtitleSegments || [{ id: Date.now(), text: "", image: DEFAULT_IMAGES[0] }],
    imageList: DEFAULT_IMAGES,
    selectedId: null,
    isPickerOpen: false,
  });

  // Update local subtitles when props change
  useEffect(() => {
    if (subtitleSegments && subtitleSegments.length > 0) {
      setEditorState(prev => ({
        ...prev,
        subtitles: subtitleSegments.map(segment => ({
          ...segment,
          image: segment.image || DEFAULT_IMAGES[0]
        }))
      }));
    }
  }, [subtitleSegments]);

  const [settingsState, setSettingsState] = useState({
    noTextTime: 0,
    sentencePause: 0,
    paragraphPause: 0,
    splitBy: "° .",
    dllitems: "⌊ ⌉",
  });

  const [audioState, setAudioState] = useState({
    segments: [{ text: "", duration: null }],
    refText: "", 
    audioFile: null,
    isProcessing: false,
    isProcessingDownload: false,
    currentSegmentPaths: [],
    showTiming: false,
    finalAudioUrl: null,
    // Add a new property to store paragraph information for SRT generation
    paragraphData: []
  });

  const [audioSettings, setAudioSettings] = useState({
    speed: 0.5,
    nfeStep: 16
  });

  const [error, setError] = useState("");

  // Send updates back to parent component
  useEffect(() => {
    if (onSegmentsUpdate && editorState.subtitles) {
      onSegmentsUpdate(editorState.subtitles);
    }
  }, [editorState.subtitles, onSegmentsUpdate]);

  // Memoized handlers
  const handleImageClick = useCallback((id) => {
    setEditorState((prev) => ({
      ...prev,
      selectedId: id,
      isPickerOpen: true,
    }));
  }, []);

  const handleSelectImage = useCallback((image) => {
    setEditorState((prev) => ({
      ...prev,
      subtitles: prev.subtitles.map((item) =>
        item.id === prev.selectedId ? { ...item, image } : item
      ),
      isPickerOpen: false,
    }));
  }, []);

  // FIXED: updateSubtitle no longer creates new subtitle elements
  const updateSubtitle = useCallback((id, newText) => {
    setEditorState((prev) => {
      const subtitles = prev.subtitles.map((subtitle) => {
        if (subtitle.id === id) {
          return { ...subtitle, text: newText };
        }
        return subtitle;
      });
      
      return {
        ...prev,
        subtitles: subtitles
      };
    });
  }, []);

  const updateImageList = useCallback((newList) => {
    setEditorState((prev) => ({
      ...prev,
      imageList: newList,
    }));
  }, []);

  const deleteSubtitle = useCallback((id) => {
    setEditorState((prev) => ({
      ...prev,
      subtitles: prev.subtitles.filter((subtitle) => subtitle.id !== id),
    }));
  }, []);

  const addSubtitleUp = useCallback((id) => {
    setEditorState((prev) => {
      const index = prev.subtitles.findIndex((s) => s.id === id);
      const newSubtitles = [...prev.subtitles];
      newSubtitles.splice(index, 0, {
        id: `${Date.now()}-${index}`,
        text: "",
        image: prev.imageList[index % prev.imageList.length],
      });
      return { ...prev, subtitles: newSubtitles };
    });
  }, []);

  const addSubtitleDown = useCallback((id) => {
    setEditorState((prev) => {
      const index = prev.subtitles.findIndex((s) => s.id === id);
      const newSubtitles = [...prev.subtitles];
      newSubtitles.splice(index + 1, 0, {
        id: `${Date.now()}-${index + 1}`,
        text: "",
        image: prev.imageList[(index + 1) % prev.imageList.length],
      });
      return { ...prev, subtitles: newSubtitles };
    });
  }, []);

  const splitSubtitle = useCallback((id, secondPart, index) => {
    setEditorState((prev) => {
      const newSubtitles = [...prev.subtitles];
      // Update the current subtitle with the first part
      newSubtitles[index] = {
        ...newSubtitles[index],
        text: newSubtitles[index].text.substring(0, newSubtitles[index].text.length - secondPart.length).trim()
      };
      
      // Insert the new subtitle with the second part
      newSubtitles.splice(index + 1, 0, {
        id: `${Date.now()}-${index}`,
        text: secondPart.trim(),
        image: prev.imageList[(index + 1) % prev.imageList.length],
      });
      
      return { ...prev, subtitles: newSubtitles };
    });
  }, []);

  const handleFileChange = useCallback((e) => {
    const file = e.target.files[0];
    if (!file) return;
    
    // Check if it's an audio file
    const validAudioTypes = ['audio/wav'];
    if (!validAudioTypes.includes(file.type)) {
      setError("Please upload a valid WAV file");
      return;
    }
    
    setAudioState((prev) => ({ ...prev, audioFile: file }));
  }, []);

  const downloadCombinedSRT = useCallback(async () => {
    try {
      if (!audioState.currentSegmentPaths?.length) {
        setError("No audio segments available");
        return;
      }

      console.log("Attempting to generate SRT for paths:", audioState.currentSegmentPaths);
      setAudioState(prev => ({ ...prev, isProcessingDownload: true }));

      // Pass both audio paths and paragraph data for more accurate SRT generation
      const response = await generateCombinedSRT(
        audioState.currentSegmentPaths, 
        audioState.paragraphData
      );
      
      if (response?.data) {
        console.log("SRT generation successful");
        
        if (response.data instanceof Blob) {
          // If response is already a Blob
          const url = URL.createObjectURL(response.data);
          const a = document.createElement('a');
          a.href = url;
          a.download = "combined.srt";
          document.body.appendChild(a);
          a.click();
          URL.revokeObjectURL(url);
          a.remove();
        } else if (typeof response.data === 'string') {
          // If response is a string
          const srtBlob = new Blob([response.data], { type: "text/plain" });
          const url = URL.createObjectURL(srtBlob);
          const a = document.createElement('a');
          a.href = url;
          a.download = "combined.srt";
          document.body.appendChild(a);
          a.click();
          URL.revokeObjectURL(url);
          a.remove();
        } else {
          // For any other type of response
          console.log("Unexpected SRT response type:", typeof response.data);
          downloadSRTContent(response.data, "combined.srt");
        }
      } else {
        throw new Error("Invalid or empty response from server");
      }
    } catch (error) {
      console.error("SRT download error:", error);
      setError(error.message || "Failed to generate SRT");
    } finally {
      setAudioState(prev => ({ ...prev, isProcessingDownload: false }));
    }
  }, [audioState.currentSegmentPaths, audioState.paragraphData]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!audioState.audioFile && ttsProvider === 'f5-tts') {
      setError("Please select a reference audio file for F5-TTS");
      return;
    }

    setAudioState(prev => ({ ...prev, isProcessing: true }));
    setParentIsProcessing(true);
    setError("");
    
    try {
      const videoResponse = await axios.post(`${getBaseURL()}/videos/`, {
        title: "New Video",
        audioPath: "",
      });
      
      const videoId = videoResponse.data.id;
      const paths = [];
      const paragraphData = []; // To keep track of paragraph info for SRT

      // Get the reference text from the first subtitle
      const refText = editorState.subtitles[0]?.text || "";

      // Process each subtitle
      for (const subtitle of editorState.subtitles) {
        if (!subtitle.text.trim()) continue;
        
        // Split text by double line breaks to handle paragraphs
        const paragraphs = splitTextIntoParagraphs(subtitle.text);
        
        // If no paragraphs found (no double line breaks), treat the entire text as one paragraph
        const textsToProcess = paragraphs.length > 0 ? paragraphs : [subtitle.text];
        
        // Process each paragraph within this subtitle
        for (const paragraphText of textsToProcess) {
          let result;
          const formData = new FormData();
          
          switch(ttsProvider) {
            case 'f5-tts':
              formData.append("ref_text", refText);
              formData.append("gen_text", paragraphText);
              formData.append("ref_audio", audioState.audioFile);
              formData.append("speed", audioSettings.speed.toString());
              result = await audioService.generateAudio(formData);
              break;

            case 'kokoro':
              // Create form data for Kokoro TTS
              const kokoroFormData = new FormData();
              kokoroFormData.append("text", paragraphText);
              kokoroFormData.append("speaker_id", voiceOrSpeaker || 'af_sarah');
              kokoroFormData.append("speed", audioSettings.speed.toString());
              
              // Generate audio using Kokoro TTS endpoint
              try {
                const kokoroResponse = await axios.post(
                  `${getBaseURL()}/generate-audio-kokoro/`, 
                  kokoroFormData,
                  {
                    headers: {
                      'Content-Type': 'multipart/form-data'
                    }
                  }
                );
                
                // Verify the response contains the audio path
                if (kokoroResponse.data && kokoroResponse.data.audio_path) {
                  result = kokoroResponse.data;
                  console.log('Kokoro TTS audio generated:', result.audio_path);
                } else {
                  console.error('Kokoro TTS response missing audio path:', kokoroResponse.data);
                  throw new Error('Failed to generate Kokoro TTS audio');
                }
              } catch (error) {
                console.error('Kokoro TTS generation error:', error);
                throw error;
              }
              break;
              
            case 'minimax':
              // Create form data for MiniMax TTS
              const minimaxFormData = new FormData();
              minimaxFormData.append("text", paragraphText);
              minimaxFormData.append("voice_id", voiceOrSpeaker || 'female-voice-1');
              minimaxFormData.append("speed", audioSettings.speed.toString());
              
              // Generate audio using MiniMax TTS endpoint
              try {
                const minimaxResponse = await axios.post(
                  `${getBaseURL()}/generate-audio-minimax/`, 
                  minimaxFormData,
                  {
                    headers: {
                      'Content-Type': 'multipart/form-data'
                    }
                  }
                );
                
                if (minimaxResponse.data && minimaxResponse.data.audio_path) {
                  result = minimaxResponse.data;
                } else {
                  throw new Error('Failed to generate MiniMax TTS audio');
                }
              } catch (error) {
                console.error('MiniMax TTS generation error:', error);
                throw error;
              }
              break;
          }
          
          if (result?.audio_path) {
            paths.push(result.audio_path);
            // Store paragraph data for SRT generation
            paragraphData.push({
              text: paragraphText,
              audioPath: result.audio_path,
              duration: result.duration || 0
            });
          }
        }
      }

      if (paths.length > 0) {
        const combinedResult = await combineAudioSegments(paths);
        if (combinedResult?.path) {
          await axios.patch(`${getBaseURL()}/videos/${videoId}`, {
            url: combinedResult.path,
            status: VideoStatus.COMPLETED
          });

          // Update state with paths, paragraph data, and final URL
          setAudioState(prev => ({
            ...prev,
            currentSegmentPaths: paths,
            paragraphData: paragraphData,
            finalAudioUrl: combinedResult.path
          }));

          onGenerationComplete({
            videoId,
            audioUrl: combinedResult.path,
            duration: combinedResult.duration || 0,
            paths,
            paragraphData
          });
        }
      }
    } catch (error) {
      console.error('Error in handleSubmit:', error);
      setError(error.message || "An error occurred during audio generation");
    } finally {
      setAudioState(prev => ({ ...prev, isProcessing: false }));
      setParentIsProcessing(false);
    }
  };

  useEffect(() => {
    if (editorState.subtitles.length > 0) {
      setAudioState(prev => ({
        ...prev,
        segments: editorState.subtitles.map(s => ({
          text: s.text,
          duration: null
        }))
      }));
    }
  }, [editorState.subtitles]);

  const splitSentences = useCallback(() => {
    try {
      const regex = new RegExp("([.!?。！？]+[\\s]*)", "g");
      const updatedSubtitles = editorState.subtitles.map(subtitle => ({
        ...subtitle,
        text: subtitle.text.replace(regex, "$1\n\n")
      }));
      setEditorState(prev => ({ ...prev, subtitles: updatedSubtitles }));
    } catch (error) {
      console.error("Split sentences error:", error);
      setError("Failed to split sentences");
    }
  }, [editorState.subtitles]);

  const deleteSpecialCharacter = useCallback(() => {
    try {
      const chars = settingsState.dllitems.replace(/\s/g, "");
      const regex = new RegExp(`[${chars}]`, "g");
      const updatedSubtitles = editorState.subtitles.map(subtitle => ({
        ...subtitle,
        text: subtitle.text.replace(regex, "")
      }));
      setEditorState(prev => ({ ...prev, subtitles: updatedSubtitles }));
    } catch (error) {
      console.error("Delete special characters error:", error);
      setError("Failed to remove special characters");
    }
  }, [editorState.subtitles, settingsState.dllitems]);

  const handleDownloadSRT = useCallback(async () => {
    try {
      if (!audioState.currentSegmentPaths?.length) {
        setError("No audio segments available");
        return;
      }

      setAudioState(prev => ({ ...prev, isProcessingDownload: true }));

      // Pass both paths and paragraph data
      const response = await generateCombinedSRT(
        audioState.currentSegmentPaths,
        audioState.paragraphData
      );
      
      if (response?.data) {
        const success = await downloadSRTContent(response.data, "combined.srt");
        if (!success) {
          throw new Error("Failed to download SRT file");
        }
      } else {
        throw new Error("Invalid response from server");
      }
    } catch (error) {
      console.error("SRT download error:", error);
      setError(error.message || "Failed to generate SRT");
    } finally {
      setAudioState(prev => ({ ...prev, isProcessingDownload: false }));
    }
  }, [audioState.currentSegmentPaths, audioState.paragraphData]);

  // Render methods
  const renderAudioControls = useMemo(() => {
    if (!audioState.finalAudioUrl) return null;

    console.log("Rendering audio controls with URL:", audioState.finalAudioUrl);
    console.log("Current segment paths:", audioState.currentSegmentPaths);

    return (
      <div className="result">
        <h2>Generated Audio</h2>
        <div className="combined-audio">
          <AudioControls audioUrl={audioState.finalAudioUrl} />
        </div>
        
        {/* Always show SRT button when finalAudioUrl exists */}
        <div className="srt-controls" style={{ marginTop: '1rem' }}>
          <button 
            onClick={handleDownloadSRT} 
            className="btn btn-success"
            disabled={audioState.isProcessingDownload || !audioState.currentSegmentPaths.length}
          >
            {audioState.isProcessingDownload ? 
              "Generating SRT..." : 
              "Download SRT Subtitles"}
          </button>
        </div>
      </div>
    );
  }, [audioState.finalAudioUrl, audioState.currentSegmentPaths, audioState.isProcessingDownload, handleDownloadSRT]);

  return (
    <div className="subtitle-editor">
      <div className="settings">
        <div className="settings-group">
          <div className="settings-item">
            <label htmlFor="noTextTime">No Text Time</label>
            <div className="settings-input-group">
              <input
                id="noTextTime"
                type="number"
                value={settingsState.noTextTime}
                onChange={(e) =>
                  setSettingsState((prev) => ({
                    ...prev,
                    noTextTime: e.target.value,
                  }))
                }
              />
              <span>ms</span>
            </div>
          </div>

          <div className="settings-item">
            <label htmlFor="sentencePause">Sentence Pause</label>
            <div className="settings-input-group">
              <input
                id="sentencePause"
                type="number"
                value={settingsState.sentencePause}
                onChange={(e) =>
                  setSettingsState((prev) => ({
                    ...prev,
                    sentencePause: e.target.value,
                  }))
                }
              />
              <span>ms</span>
            </div>
          </div>

          <div className="settings-item">
            <label htmlFor="paragraphPause">Paragraph Pause</label>
            <div className="settings-input-group">
              <input
                id="paragraphPause"
                type="number"
                value={settingsState.paragraphPause}
                onChange={(e) =>
                  setSettingsState((prev) => ({
                    ...prev,
                    paragraphPause: e.target.value,
                  }))
                }
              />
              <span>ms</span>
            </div>
          </div>
        </div>

        <div className="settings-group">
          <div className="settings-item">
            <label htmlFor="splitBy">Split By</label>
            <div className="settings-input-group">
              <input
                id="splitBy"
                type="text"
                value={settingsState.splitBy}
                onChange={(e) =>
                  setSettingsState((prev) => ({
                    ...prev,
                    splitBy: e.target.value,
                  }))
                }
              />
              <button onClick={splitSentences}>Split</button>
            </div>
          </div>

          <div className="settings-item">
            <label htmlFor="dllitems">Special Characters</label>
            <div className="settings-input-group">
              <input
                id="dllitems"
                type="text"
                value={settingsState.dllitems}
                onChange={(e) =>
                  setSettingsState((prev) => ({
                    ...prev,
                    dllitems: e.target.value,
                  }))
                }
              />
              <button onClick={deleteSpecialCharacter}>Delete</button>
            </div>
          </div>
        </div>

        <div className="settings-group">
          <div className="settings-item">
            <label htmlFor="speed">Speech Speed</label>
            <div className="settings-input-group">
              <input
                id="speed"
                type="range"
                min="0.1"
                max="2.0"
                step="0.1"
                value={audioSettings.speed}
                onChange={(e) => setAudioSettings(prev => ({
                  ...prev,
                  speed: parseFloat(e.target.value)
                }))}
              />
              <span>{audioSettings.speed}x</span>
            </div>
          </div>
        </div>
      </div>

      <SubtitleList
        subtitles={editorState.subtitles}
        onUpdateSubtitle={updateSubtitle}
        onDeleteSubtitle={deleteSubtitle}
        onAddSubtitleUp={addSubtitleUp}
        onAddSubtitleDown={addSubtitleDown}
        onImageClick={handleImageClick}
        onSplitSubtitle={splitSubtitle}
      />

      {editorState.isPickerOpen && (
        <FilePicker
          onClose={() =>
            setEditorState((prev) => ({ ...prev, isPickerOpen: false }))
          }
          onSelect={handleSelectImage}
          imageList={editorState.imageList}
          updateImageList={updateImageList}
        />
      )}

      <div className="audio-section">
        <TTSSelector 
          onProviderChange={handleProviderChange}
          selectedProvider={ttsProvider}
          disabled={audioState.isProcessing}
        />
        
        {ttsProvider === 'f5-tts' && (
          <div className="file-input-container">
            <label htmlFor="referenceAudio">Reference Audio:</label>
            <input
              type="file"
              id="referenceAudio"
              onChange={handleFileChange}
              accept="audio/wav"
              className="audio-input"
              required
            />
          </div>
        )}
        
        <div className="settings-group">
          <div className="settings-item">
            <label htmlFor="speed">Speech Speed</label>
            <div className="settings-input-group">
              <input
                id="speed"
                type="range"
                min="0.1"
                max="2.0"
                step="0.1"
                value={audioSettings.speed}
                onChange={(e) => setAudioSettings(prev => ({
                  ...prev,
                  speed: parseFloat(e.target.value)
                }))}
              />
              <span>{audioSettings.speed}x</span>
            </div>
          </div>
        </div>
        
        {error && <div className="error-message">{error}</div>}
        {renderAudioControls}
        
        <button
          onClick={handleSubmit}
          type="button"
          className={`generate-btn ${audioState.isProcessing ? 'processing' : ''}`}
          disabled={audioState.isProcessing || (ttsProvider === 'f5-tts' && !audioState.audioFile)}
        >
          {audioState.isProcessing ? "Generating..." : "Generate Audio"}
        </button>
      </div>
    </div>
  );
};

SubtitleEditor.propTypes = {
  subtitleSegments: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.string,
      text: PropTypes.string,
      image: PropTypes.string
    })
  ),
  onSegmentsUpdate: PropTypes.func,
  setIsProcessing: PropTypes.func.isRequired,
  onGenerationComplete: PropTypes.func.isRequired
};

SubtitleEditor.defaultProps = {
  subtitleSegments: [{ id: Date.now().toString(), text: "", image: null }],
  onSegmentsUpdate: () => {}
};

export default SubtitleEditor;