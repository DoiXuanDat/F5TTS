import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import SubtitleEditor from "../../components/subtitle/SubtitleEditor";
import "./ImportText.css";

const ImportText = () => {
  const navigate = useNavigate();
  const [subtitleText, setSubtitleText] = useState("");
  const [regexPath, setRegexPath] = useState("([，、.「」？；：！])");
  const [dllitems, setDllitems] = useState("⌊ ⌉");
  const [step, setStep] = useState(1);
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

  const nextStep = () => {
    if (step < 2) {
      document.querySelector(".paper").classList.add("slide-out-left");
      setTimeout(() => {
        setStep(step + 1);
        document.querySelector(".paper").classList.remove("slide-out-left");
        document.querySelector(".paper").classList.add("slide-in-right");
      }, 300);
    }
  };

  const prevStep = () => {
    if (step > 1) {
      document.querySelector(".paper").classList.add("slide-out-right");
      setTimeout(() => {
        setStep(step - 1);
        document.querySelector(".paper").classList.remove("slide-out-right");
        document.querySelector(".paper").classList.add("slide-in-left");
      }, 300);
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
      <h2 className="text-center mt-4">Chỉnh sửa nội dung Subtitle</h2>
      <div className="toolbar">
        <label>
          <i
            className={`bi ${
              step === 1 ? "bi-1-circle-fill" : "bi-check-circle-fill"
            } me-2 text-primary`}
          ></i>
          Chia đoạn văn bản
        </label>
        <hr />
        <i
          className={`bi bi-2-circle-fill me-2  ${
            step === 1 ? "text-secondary" : "text-primary"
          }`}
        ></i>
        Chọn hình ảnh - Video
      </div>
      <hr className="line" />

      {/* File Upload Step */}
      {step === 1 && (
        <div className="paper">
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
          <div className="buttonContainer">
            <button className="button btn btn-primary" onClick={nextStep}>
              Tiếp theo
            </button>
          </div>
        </div>
      )}

      {/* Subtitle Editor Step */}
      {step === 2 && (
        <div className="paper">
          <SubtitleEditor 
            subtitleText={subtitleText} 
            onGenerationComplete={handleGenerationComplete}
          />
          <div className="buttonContainer mt-3">
            <button 
              className="btn btn-danger me-4" 
              onClick={prevStep}
            >
              Quay lại
            </button>
            <button 
              className="btn btn-success"
              onClick={handleSave}
              disabled={!isGenerationComplete}
            >
              Lưu và tiếp tục
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default ImportText;
