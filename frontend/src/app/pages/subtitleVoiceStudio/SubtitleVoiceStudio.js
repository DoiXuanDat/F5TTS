import React, { useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import SubtitleEditor from "../../components/subtitle/SubtitleEditor";
import FileUploadSection from "../../components/fileUpload/FileUploadSection";
import "./SubtitleVoiceStudio.css";

function SubtitleVoiceStudio() {
  const navigate = useNavigate();
  const [regexPath, setRegexPath] = useState("([，、.「」？；：！])");
  const [dllitems, setDllitems] = useState("⌊ ⌉");
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
      alert("Invalid Regex pattern. Please check again!");
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

  const parseSrtContent = useCallback((content) => {
    const regex = /(\d+)\r?\n(\d{2}:\d{2}:\d{2}[,\.]\d{3}) *--> *(\d{2}:\d{2}:\d{2}[,\.]\d{3})[\r\n]+([\s\S]*?)(?=[\r\n]+\d+[\r\n]+\d{2}:\d{2}:\d{2}[,\.]\d{3} *--> *\d{2}:\d{2}:\d{2}[,\.]\d{3}|$)/g;
    const subtitles = [];
    let match;

    while ((match = regex.exec(content)) !== null) {
      subtitles.push({
        id: Date.now() + '-' + match[1],
        text: match[4].trim()
          .replace(/<[^>]*>/g, '')
          .replace(/\r\n|\r|\n/g, ' ')
          .trim(),
        image: null
      });
    }

    return subtitles;
  }, []);

  const handleFileUpload = useCallback((event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    console.log("File selected:", file.name, file.type, file.size, "bytes");

    const reader = new FileReader();
    reader.onload = (e) => {
      if (e.target && typeof e.target.result === "string") {
        let content = e.target.result;
        
        if (file.name.endsWith(".srt")) {
          console.log("Processing as SRT file");
          const parsedSubtitles = parseSrtContent(content);
          setEditorState(prev => ({
            ...prev,
            subtitles: parsedSubtitles
          }));
        }
      }
    };

    reader.onerror = (error) => {
      console.error("File reading error:", error);
      alert("Error reading file: " + error);
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

  return (
    <div className="container">
      <div className="paper">
        <FileUploadSection
          regexPath={regexPath}
          dllitems={dllitems}
          onRegexChange={setRegexPath}
          onDllitemsChange={setDllitems}
          onSplitText={handleSplitText}
          onDeleteSpecialChars={handleDeleteSpecialChars}
          onFileUpload={handleFileUpload}
        />
        
        <SubtitleEditor 
          subtitleSegments={editorState.subtitles}
          setIsProcessing={(isProcessing) => setEditorState((prev) => ({ ...prev, isGenerating: isProcessing }))}
          onGenerationComplete={handleGenerationComplete}
        />
        
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