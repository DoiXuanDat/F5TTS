// This should be updated in frontend/src/app/pages/importText/ImportText.js

import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import SubtitleEditor from "../../components/subtitle/SubtitleEditor";
import "./ImportText.css";

const ImportText = () => {
  const navigate = useNavigate();
  const [subtitleText, setSubtitleText] = useState("");
  const [regexPath, setRegexPath] = useState("([，、.「」？；：！])");
  const [dllitems, setDllitems] = useState("⌊ ⌉");
  const [isGenerationComplete, setIsGenerationComplete] = useState(false);
  const [generatedData, setGeneratedData] = useState(null);

  const parseSrtContent = (srtContent) => {
    const regex =
      /(\d+)\r?\n(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})\r?\n([\s\S]*?)(?:\r?\n\r?\n|$)/g;

    let parsedText = "";
    let match;

    // Extract all subtitle text entries
    while ((match = regex.exec(srtContent)) !== null) {
      const subtitleText = match[4].trim();
      parsedText += subtitleText + "\n\n";
    }

    return parsedText.trim();
  };

  const handleFileUpload = (event) => {
    const file = event.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (e) => {
        if (e.target && typeof e.target.result === "string") {
          if (file.name.endsWith(".srt")) {
            const parsedText = parseSrtContent(e.target.result);
            setSubtitleText(parsedText);
          } else {
            setSubtitleText(e.target.result);
          }
        }
      };
      reader.readAsText(file);
    }
  };

  function deleteSpecialCharacter() {
    const updatedText = subtitleText.replace(
      new RegExp(`[${dllitems.replace(/\s/g, "")}]`, "g"),
      ""
    );
    setSubtitleText(updatedText);
  }

  const splitTextByRegex = () => {
    try {
      const regex = new RegExp(regexPath, "g");
      const updatedSubtitles = subtitleText.replace(regex, "$1\n\n");
      setSubtitleText(updatedSubtitles);
    } catch (error) {
      console.error("Lỗi Regex:", error);
      alert("Regex không hợp lệ. Hãy kiểm tra lại!");
    }
  };

  const handleGenerationComplete = (data) => {
    setIsGenerationComplete(true);
    setGeneratedData(data);
  };

  const handleSave = () => {
    // Create a new video entry
    const newVideo = {
      id: `VID${Date.now()}`,
      title: subtitleText.slice(0, 30) + "...", // First 30 chars as title
      status: "completed",
      createdAt: new Date().toISOString(),
      url: generatedData?.audioUrl || "",
    };

    // Here you would typically save to your backend
    // For now, we'll just navigate to the video list
    navigate("/video-list");
  };

  return (
    <div className="container">
      {/* Removed the title */}
      
      {/* Removed the navigation toolbar since we're merging sections */}
      
      <div className="paper">
        {/* File upload and text processing section */}
        <div className="formRegex">
          <label>Regex chia dòng:</label>
          <input
            type="text"
            className="regexInput"
            placeholder="Enter regex"
            value={regexPath}
            onChange={(e) => setRegexPath(e.target.value)}
          />
          <button
            className="button btn btn-primary"
            onClick={splitTextByRegex}
          >
            Chia
          </button>
        </div>
        <div className="deleteSpecialChars">
          <label>Xóa ký tự đặc biệt:</label>
          <input
            type="text"
            className="deleteSpecialCharsInput"
            placeholder="Nhập ký tự cần xóa"
            value={dllitems}
            onChange={(e) => setDllitems(e.target.value)}
          />
          <button
            className="button btn btn-danger"
            onClick={deleteSpecialCharacter}
          >
            Xóa
          </button>
        </div>
        <input
          className="mt-1"
          type="file"
          accept=".srt,.ass"
          onChange={handleFileUpload}
          id="file-upload"
          style={{ display: "none" }}
        />
        <label htmlFor="file-upload" className="button btn btn-info">
          Chọn file (.srt, .ass)
        </label>
        <textarea
          className="textarea"
          placeholder="File content will appear here..."
          value={subtitleText}
          onChange={(e) => setSubtitleText(e.target.value)}
        />
        <p className="length">
          Kí tự: {subtitleText.length} — Dòng:{" "}
          {subtitleText.split("\n").length}
        </p>
        
        {/* Subtitle Editor for image selection and TTS generation */}
        <SubtitleEditor 
          subtitleText={subtitleText} 
          setIsProcessing={(isProcessing) => {}}
          onGenerationComplete={handleGenerationComplete}
        />
        
        <div className="buttonContainer mt-3">
          <button 
            className="btn btn-success"
            onClick={handleSave}
            disabled={!isGenerationComplete}
          >
            Lưu và tiếp tục
          </button>
        </div>
      </div>
    </div>
  );
};

export default ImportText;