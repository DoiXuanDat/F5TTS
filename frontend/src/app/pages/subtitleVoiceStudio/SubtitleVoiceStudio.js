import React, { useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import SubtitleEditor from "../../components/subtitle/SubtitleEditor";
import FileUploadSection from "../../components/fileUpload/FileUploadSection";
import TextSegmentForm from "../../components/textSegment/TextSegmentForm";
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
import "./SubtitleVoiceStudio.css";

function SubtitleVoiceStudio() {
  const navigate = useNavigate();
  const [subtitleText, setSubtitleText] = useState("");
  const [regexPath, setRegexPath] = useState("([，、.「」？；：！])");
  const [dllitems, setDllitems] = useState("⌊ ⌉");
  const [step, setStep] = useState(1);

  const [segments, setSegments] = useState([{ text: "", duration: null }]);
  const [refText, setRefText] = useState("");
  const [audioFile, setAudioFile] = useState(null);
  const [currentSegmentPaths, setCurrentSegmentPaths] = useState([]);
  const [showTiming, setShowTiming] = useState(false);
  const [error, setError] = useState("");
  const [finalAudioUrl, setFinalAudioUrl] = useState(null);
  const [isGenerating, setIsGenerating] = useState(false);

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
    setError("");
    setIsGenerating(true); // Start generating
    try {
      const paths = [];
      for (let i = 0; i < segments.length; i++) {
        const formData = new FormData();
        formData.append("ref_text", refText);
        formData.append("gen_text", segments[i].text);
        formData.append("ref_audio", audioFile);
        formData.append("segment_index", i.toString());

        const result = await audioService.generateAudio(formData);
        console.log("Generated audio path:", result.full_path);
        paths.push(result.full_path);
      }

      console.log("Paths to combine:", paths);

      if (paths.length > 0) {
        const combinedResult = await combineAudioSegments(paths);
        setCurrentSegmentPaths([...paths]);
        setFinalAudioUrl(combinedResult.path); // Just use the relative path
      }
    } catch (error) {
      console.error("Error in handleSubmit:", error);
      setError(error.message || "An error occurred");
    } finally {
      setIsGenerating(false); // End generating
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
        const srtBlob = new Blob([response.data], { type: "text/plain" });
        createDownloadLink(srtBlob, "combined.srt");
      } else {
        throw new Error("Invalid response from server");
      }
    } catch (err) {
      console.error("SRT download error:", err);
      setError("Failed to download SRT: " + (err.message || "Unknown error"));
    }
  };

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

  const handleSplitText = useCallback(() => {
    try {
      const regex = new RegExp(regexPath, "g");
      const updatedSubtitles = subtitleText.replace(regex, "$1\n\n");
      setSubtitleText(updatedSubtitles);
    } catch (error) {
      console.error("Regex Error:", error);
      alert("Invalid Regex pattern. Please check again!");
    }
  }, [regexPath, subtitleText]);

  const handleDeleteSpecialChars = useCallback(() => {
    const updatedText = subtitleText.replace(
      new RegExp(`[${dllitems.replace(/\s/g, "")}]`, "g"),
      ""
    );
    setSubtitleText(updatedText);
  }, [dllitems, subtitleText]);

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

  const handleSave = () => {
    // TODO: Thêm logic lưu dữ liệu nếu cần
    navigate("/list");
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
          <FileUploadSection
            regexPath={regexPath}
            dllitems={dllitems}
            onRegexChange={setRegexPath}
            onDllitemsChange={setDllitems}
            onSplitText={handleSplitText}
            onDeleteSpecialChars={handleDeleteSpecialChars}
            onFileUpload={handleFileUpload}
          />

          <TextSegmentForm
            segments={segments}
            refText={refText}
            showTiming={showTiming}
            onRefTextChange={setRefText}
            onSegmentChange={handleSegmentChange}
            onRemoveSegment={handleRemoveSegment}
            onAddSegment={handleAddSegment}
            onShowTimingToggle={() => setShowTiming(!showTiming)}
            onSubmit={handleSubmit}
          />

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
            setIsProcessing={setIsGenerating}
          />
          <div className="buttonContainer">
            <button
              className="button btn btn-danger me-4"
              onClick={prevStep}
              disabled={isGenerating}
            >
              Back
            </button>
            <button
              className="button btn btn-success"
              onClick={handleSave}
              disabled={isGenerating || !finalAudioUrl}
            >
              Lưu
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default SubtitleVoiceStudio;
