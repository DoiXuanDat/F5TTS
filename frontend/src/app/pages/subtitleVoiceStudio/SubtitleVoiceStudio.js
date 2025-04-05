import React, { useState, useCallback, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import SubtitleEditor from "../../components/subtitle/SubtitleEditor";
import FileUploadSection from "../../components/fileUpload/FileUploadSection";
import AudioUploader from "../../components/audio/AudioUploader";
import { transcriptionService } from "../../services/transcriptionService";
import "./SubtitleVoiceStudio.css";

function SubtitleVoiceStudio() {
  const navigate = useNavigate();
  const [regexPath, setRegexPath] = useState("([，、.「」？；：！])");
  const [dllitems, setDllitems] = useState("⌊ ⌉");
  const [activeTab, setActiveTab] = useState('text'); // 'text', 'audio', or 'srt'
  const [error, setError] = useState(null);
  
  const [editorState, setEditorState] = useState({
    subtitles: [{ id: Date.now().toString(), text: "", image: null }],
    isGenerating: false,
    isGenerationComplete: false,
    generatedData: null
  });

  const handleSplitText = useCallback(() => {
    try {
      const regex = new RegExp(regexPath, "g");
      const updatedSubtitles = editorState.subtitles.map((subtitle) => ({
        ...subtitle,
        text: subtitle.text.replace(regex, "$1\n\n")
      }));
      setEditorState((prev) => ({ ...prev, subtitles: updatedSubtitles }));
    } catch (error) {
      console.error("Regex Error:", error);
      setError("Invalid Regex pattern. Please check again!");
    }
  }, [regexPath, editorState.subtitles]);

  const handleDeleteSpecialChars = useCallback(() => {
    const updatedSubtitles = editorState.subtitles.map((subtitle) => ({
      ...subtitle,
      text: subtitle.text.replace(
        new RegExp(`[${dllitems.replace(/\s/g, "")}]`, "g"),
        ""
      )
    }));
    setEditorState((prev) => ({ ...prev, subtitles: updatedSubtitles }));
  }, [dllitems, editorState.subtitles]);

  const handleTranscriptionComplete = (text) => {
    // Update the first subtitle or create a new one with the transcribed text
    const newSubtitles = editorState.subtitles.length > 0 
      ? editorState.subtitles.map((subtitle, index) => 
          index === 0 ? { ...subtitle, text } : subtitle
        )
      : [{ id: Date.now().toString(), text, image: null }];
      
    setEditorState(prev => ({
      ...prev,
      subtitles: newSubtitles
    }));
    
    // Switch to text tab to show results
    setActiveTab('text');
  };

  const parseSrtContent = useCallback((content) => {
    try {
      const subtitles = transcriptionService.parseSrtFile(content);
      
      if (subtitles.length === 0) {
        setError("No valid subtitles found in the SRT file");
        return [];
      }
      
      return subtitles;
    } catch (error) {
      console.error("SRT parsing error:", error);
      setError("Failed to parse SRT file");
      return [];
    }
  }, []);

  const handleFileUpload = useCallback((event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    console.log("File selected:", file.name, file.type, file.size, "bytes");
    setError(null);

    const reader = new FileReader();
    reader.onload = (e) => {
      if (e.target && typeof e.target.result === "string") {
        let content = e.target.result;
        
        if (file.name.endsWith(".srt")) {
          console.log("Processing as SRT file");
          const parsedSubtitles = parseSrtContent(content);
          
          if (parsedSubtitles.length > 0) {
            setEditorState(prev => ({
              ...prev,
              subtitles: parsedSubtitles
            }));
          }
        } else {
          // For other text files, just put content in first subtitle
          setEditorState(prev => ({
            ...prev,
            subtitles: [
              { 
                id: Date.now().toString(), 
                text: content,
                image: null 
              }
            ]
          }));
        }
      }
    };

    reader.onerror = (error) => {
      console.error("File reading error:", error);
      setError("Error reading file: " + error);
    };

    reader.readAsText(file);
  }, [parseSrtContent]);

  const handleGenerationComplete = (data) => {
    setEditorState((prev) => ({
      ...prev,
      isGenerationComplete: true,
      generatedData: data
    }));
  };

  const handleSave = () => {
    if (!editorState.generatedData?.audioUrl) {
      setError("Please generate audio before saving");
      return;
    }

    const newVideo = {
      id: `VID${Date.now()}`,
      title: editorState.subtitles[0]?.text.slice(0, 30) + "...",
      status: "completed",
      createdAt: new Date().toISOString(),
      url: editorState.generatedData.audioUrl,
    };

    navigate("/video-list");
  };

  const handleError = (errorMessage) => {
    setError(errorMessage);
  };

  // Clear error after 5 seconds
  useEffect(() => {
    if (error) {
      const timer = setTimeout(() => {
        setError(null);
      }, 5000);
      
      return () => clearTimeout(timer);
    }
  }, [error]);

  return (
    <div className="container">
      <div className="paper">
        {/* Tab Navigation */}
        <div className="input-method-tabs">
          <button 
            className={`tab-button ${activeTab === 'text' ? 'active' : ''}`}
            onClick={() => setActiveTab('text')}
          >
            Text Input
          </button>
          <button 
            className={`tab-button ${activeTab === 'audio' ? 'active' : ''}`}
            onClick={() => setActiveTab('audio')}
          >
            Audio Transcription
          </button>
          <button 
            className={`tab-button ${activeTab === 'srt' ? 'active' : ''}`}
            onClick={() => setActiveTab('srt')}
          >
            SRT Import
          </button>
        </div>
        
        {/* Error Messages */}
        {error && (
          <div className="error-message">
            {error}
          </div>
        )}
        
        {/* Text Input Tab */}
        {activeTab === 'text' && (
          <div className="input-section">
            <div className="formRegex">
              <label>Split sentences by:</label>
              <input
                type="text"
                className="regexInput"
                placeholder="Enter regex"
                value={regexPath}
                onChange={(e) => setRegexPath(e.target.value)}
              />
              <button
                className="button btn btn-primary"
                onClick={handleSplitText}
              >
                Split
              </button>
            </div>
            <div className="deleteSpecialChars">
              <label>Remove special characters:</label>
              <input
                type="text"
                className="deleteSpecialCharsInput"
                placeholder="Characters to remove"
                value={dllitems}
                onChange={(e) => setDllitems(e.target.value)}
              />
              <button
                className="button btn btn-danger"
                onClick={handleDeleteSpecialChars}
              >
                Remove
              </button>
            </div>
          </div>
        )}
        
        {/* Audio Transcription Tab */}
        {activeTab === 'audio' && (
          <div className="input-section">
            <AudioUploader 
              onTranscriptionComplete={handleTranscriptionComplete}
              onError={handleError}
            />
          </div>
        )}
        
        {/* SRT Import Tab */}
        {activeTab === 'srt' && (
          <div className="input-section">
            <FileUploadSection
              regexPath={regexPath}
              dllitems={dllitems}
              onRegexChange={setRegexPath}
              onDllitemsChange={setDllitems}
              onSplitText={handleSplitText}
              onDeleteSpecialChars={handleDeleteSpecialChars}
              onFileUpload={handleFileUpload}
            />
          </div>
        )}
        
        {/* Subtitle Editor (common to all tabs) */}
        <SubtitleEditor 
          subtitleSegments={editorState.subtitles}
          setIsProcessing={(isProcessing) => setEditorState(prev => ({ 
            ...prev, 
            isGenerating: isProcessing 
          }))}
          onGenerationComplete={handleGenerationComplete}
        />
        
        {/* Save Button */}
        <div className="buttonContainer mt-3">
          <button 
            className="btn btn-success"
            onClick={handleSave}
            disabled={!editorState.isGenerationComplete}
          >
            Save and Continue
          </button>
        </div>
      </div>
    </div>
  );
}

export default SubtitleVoiceStudio;