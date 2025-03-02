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
  const [segments, setSegments] = useState([{ text: "", duration: null }]);
  const [refText, setRefText] = useState("");
  const [audioFile, setAudioFile] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [currentSegmentPaths, setCurrentSegmentPaths] = useState([]);
  const [showTiming, setShowTiming] = useState(false);
  const [error, setError] = useState("");
  const [finalAudioUrl, setFinalAudioUrl] = useState(null);

  const handleAddSegment = () => {
    setSegments([...segments, { text: "", duration: null }]);
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

            const result = await audioService.generateAudio(formData);
            console.log('Generated audio path:', result.full_path);
            paths.push(result.full_path);
        }

        console.log('Paths to combine:', paths);

        if (paths.length > 0) {
            const combinedResult = await combineAudioSegments(paths);
            setCurrentSegmentPaths([...paths]);
            setFinalAudioUrl(combinedResult.path); // Just use the relative path
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
        <div className="form-group">
          <label htmlFor="ref_text">Reference Text:</label>
          <input
            type="text"
            id="ref_text"
            value={refText}
            onChange={(e) => setRefText(e.target.value)}
            required
            placeholder="Enter reference text"
          />
        </div>

        <div className="timing-controls">
          <button
            type="button"
            onClick={() => setShowTiming(!showTiming)}
            className="btn"
          >
            {showTiming ? "Hide Timing Info" : "Show Timing Info"}
          </button>
        </div>

        {segments.map((segment, index) => (
          <div key={index} className="segment-group">
            <div className="segment-header">
              <h3>Text Segment {index + 1}</h3>
              {segments.length > 1 && (
                <button
                  type="button"
                  className="btn remove-segment"
                  onClick={() => handleRemoveSegment(index)}
                >
                  Remove
                </button>
              )}
            </div>
            <textarea
              className="gen-text-segment"
              value={segment.text}
              onChange={(e) => handleSegmentChange(index, e.target.value)}
              required
              placeholder="Enter text to generate"
            />
            {showTiming && (
              <div className="timing-info">
                <span className="duration">
                  Duration: {segment.duration || "--"}
                </span>
              </div>
            )}
          </div>
        ))}

        <button
          type="button"
          className="btn add-segment-btn"
          onClick={handleAddSegment}
        >
          Add Another Segment
        </button>

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