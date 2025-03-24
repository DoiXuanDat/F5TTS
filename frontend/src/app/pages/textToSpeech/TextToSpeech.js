import React, { useState } from "react";
import "./TextToSpeech.css";
import {
  audioService,
  combineAudioSegments,
  generateCombinedSRT,
} from "../../services/api";
import {
  formatTime,
  createDownloadLink,
  validateAudioFile,
} from "../../services/audioProcessing";
import AudioControls from "../../components/audio/AudioControls";
import { BASE_URL } from "../../services/api";

const TextToSpeech = ({ setIsProcessing: setParentIsProcessing }) => {
  const [segments, setSegments] = useState([{ text: "" }]);
  const [refText, setRefText] = useState("");
  const [audioFile, setAudioFile] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [currentSegmentPaths, setCurrentSegmentPaths] = useState([]);
  const [error, setError] = useState("");
  const [finalAudioUrl, setFinalAudioUrl] = useState(null);
  const [audioSettings, setAudioSettings] = useState({
    speed: 0.5,
    nfeStep: 16
  });

  const handleAddSegment = () => {
    setSegments([...segments, { text: "" }]);
  };

  const handleRemoveSegment = (index) => {
    const newSegments = segments.filter((_, i) => i !== index);
    setSegments(newSegments);
  };

  const handleSegmentChange = (index, value) => {
    const newSegments = [...segments];
    newSegments[index].text = value;
    setSegments(newSegments);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsProcessing(true);
    setParentIsProcessing(true);
    setError("");
    try {
        const paths = [];
        for (let i = 0; i < segments.length; i++) {
            const formData = new FormData();
            formData.append("ref_text", refText);
            formData.append("gen_text", segments[i].text);
            formData.append("ref_audio", audioFile);
            formData.append("segment_index", i.toString());
            formData.append("speed", audioSettings.speed.toString());
            formData.append("nfe_step", audioSettings.nfeStep.toString());

            const result = await audioService.generateAudio(formData);
            console.log(`Segment ${i} result:`, result);

            if (!result || !result.audio_path) {
                throw new Error(`Failed to generate audio for segment ${i}`);
            }

            paths.push(result.audio_path);
        }

        console.log('Generated audio paths:', paths);

        if (paths.length > 0) {
            const combinedResult = await combineAudioSegments(paths);
            if (combinedResult && combinedResult.path) {
                setCurrentSegmentPaths([...paths]);
                setFinalAudioUrl(combinedResult.path);
            } else {
                throw new Error('Invalid response from combine audio');
            }
        }

    } catch (error) {
        console.error('Error in handleSubmit:', error);
        setError(error.message || "An error occurred");
    } finally {
        setIsProcessing(false);
        setParentIsProcessing(false);
    }
};

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (!validateAudioFile(file)) {
      setError("Please upload a valid WAV file");
      return;
    }
    setAudioFile(file);
  };

  const downloadCombinedSRT = async () => {
    try {
      if (!currentSegmentPaths || currentSegmentPaths.length === 0) {
        setError("No audio segments available for SRT generation");
        return;
      }
  
      console.log("Generating SRT for paths:", currentSegmentPaths);
      
      const response = await generateCombinedSRT(currentSegmentPaths);
      
      if (response && response.data) {
        const srtBlob = new Blob([response.data], { type: 'text/plain' });
        createDownloadLink(srtBlob, "combined.srt");
      } else {
        throw new Error("Invalid response from server");
      }
    } catch (err) {
      console.error("SRT download error:", err);
      setError("Failed to download SRT: " + (err.message || "Unknown error"));
    }
  };

  return (
    <div className="container">
      <h1>Advanced Text-to-Speech Generator</h1>
      <form onSubmit={handleSubmit}>
        <TextSegmentForm
          segments={segments}
          refText={refText}
          onRefTextChange={setRefText}
          onSegmentChange={handleSegmentChange}
          onRemoveSegment={handleRemoveSegment}
          onAddSegment={handleAddSegment}
          onSubmit={handleSubmit}
        />
        
        <div className="form-group">
          <label htmlFor="referenceAudio">
            Upload Audio File (WAV format):
          </label>
          <input
            type="file"
            id="referenceAudio"
            onChange={handleFileChange}
            accept="audio/wav"
            required
          />
        </div>

        <div className="form-group">
          <label htmlFor="speed">Speech Speed</label>
          <div className="input-group settings-input-group">
            <input
              type="range"
              id="speed"
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

        <button
          type="submit"
          className="btn generate-btn"
          disabled={isProcessing}
        >
          {isProcessing ? "Generating..." : "Generate Audio"}
        </button>
      </form>

      {error && <div className="error">{error}</div>}

      {finalAudioUrl && (
        <div className="result">
          <h2>Generated Audio</h2>
          <div className="combined-audio">
            <h3>Combined Audio</h3>
            <AudioControls audioUrl={finalAudioUrl} />
          </div>
          <div className="srt-controls">
            <button onClick={downloadCombinedSRT} className="btn srt-btn">
              Download Combined SRT
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default TextToSpeech;