import React, { useState, useEffect, useCallback, useMemo } from "react";
import PropTypes from "prop-types";
import FilePicker from "../common/filePicker/FilePicker";
import SubtitleList from "./SubtitleList";
import Settings from "../common/settings/Settings";
import AudioControls from "../audio/AudioControls";
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
import "./SubtitleEditor.css";

const DEFAULT_IMAGES = [
  require("../../assets/images/30.png"),
  require("../../assets/images/31.png"),
  require("../../assets/images/32.png"),
  require("../../assets/images/33.png"),
];

const SubtitleEditor = ({
  subtitleText,
  setIsProcessing: setParentIsProcessing,
}) => {
  // State management with logical grouping
  const [editorState, setEditorState] = useState({
    subtitles: [],
    imageList: DEFAULT_IMAGES,
    selectedId: null,
    isPickerOpen: false,
  });

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
    currentSegmentPaths: [],
    showTiming: false,
    finalAudioUrl: null,
  });

  const [error, setError] = useState("");

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

  const updateSubtitle = useCallback((id, newText) => {
    setEditorState((prev) => ({
      ...prev,
      subtitles: prev.subtitles.map((subtitle) =>
        subtitle.id === id ? { ...subtitle, text: newText } : subtitle
      ),
    }));
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
      newSubtitles.splice(index, 0, {
        id: `${Date.now()}-${index}`,
        text: secondPart,
        image: prev.imageList[index % prev.imageList.length],
      });
      return { ...prev, subtitles: newSubtitles };
    });
  }, []);

  const handleFileChange = useCallback((e) => {
    const file = e.target.files[0];
    if (!validateAudioFile(file)) {
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

      const response = await generateCombinedSRT(
        audioState.currentSegmentPaths
      );
      if (response?.data) {
        const srtBlob = new Blob([response.data], { type: "text/plain" });
        createDownloadLink(srtBlob, "combined.srt");
      }
    } catch (error) {
      setError(error.message || "Failed to generate SRT");
    }
  }, [audioState.currentSegmentPaths]);

  const processAudioSegments = useCallback(async () => {
    const paths = [];
    for (const segment of audioState.segments) {
      if (!segment.text.trim()) continue;

      const formData = new FormData();
      formData.append("ref_text", audioState.refText);
      formData.append("gen_text", segment.text);
      formData.append("ref_audio", audioState.audioFile);

      const result = await audioService.generateAudio(formData);
      paths.push(result.full_path);
    }
    return paths;
  }, [audioState.segments, audioState.refText, audioState.audioFile]);

  const splitSentences = useCallback(() => {
    try {
      const regex = new RegExp(settingsState.splitBy, "g");
      setEditorState((prev) => ({
        ...prev,
        subtitles: prev.subtitles.map((subtitle) => ({
          ...subtitle,
          text: subtitle.text.replace(regex, "$1\n"),
        })),
      }));
    } catch (error) {
      setError("Invalid regex pattern");
    }
  }, [settingsState.splitBy]);

  const deleteSpecialCharacter = useCallback(() => {
    const pattern = new RegExp(
      `[${settingsState.dllitems.replace(/\s/g, "")}]`,
      "g"
    );
    setEditorState((prev) => ({
      ...prev,
      subtitles: prev.subtitles.map((subtitle) => ({
        ...subtitle,
        text: subtitle.text.replace(pattern, ""),
      })),
    }));
  }, [settingsState.dllitems]);

  // Audio processing handlers
  const handleSubmit = useCallback(
    async (e) => {
      e.preventDefault();
      setAudioState((prev) => ({ ...prev, isProcessing: true }));
      setParentIsProcessing(true);
      setError("");

      try {
        const paths = await processAudioSegments();
        if (paths.length > 0) {
          const combinedResult = await combineAudioSegments(paths);
          setAudioState((prev) => ({
            ...prev,
            currentSegmentPaths: paths,
            finalAudioUrl: combinedResult.path,
          }));
        }
      } catch (error) {
        console.error("Error in handleSubmit:", error);
        setError(error.message || "An error occurred");
      } finally {
        setAudioState((prev) => ({ ...prev, isProcessing: false }));
        setParentIsProcessing(false);
      }
    },
    [audioState.segments, setParentIsProcessing]
  );

  // Effect for processing subtitle text
  useEffect(() => {
    if (subtitleText) {
      const paragraphs = subtitleText
        .split("\n\n")
        .filter((p) => p.trim() !== "");

      const newSubtitles = paragraphs.map((paragraph, index) => ({
        id: `${Date.now()}-${index}`,
        text: paragraph.trim(),
        image: editorState.imageList[index % editorState.imageList.length],
      }));

      setEditorState((prev) => ({ ...prev, subtitles: newSubtitles }));
    }
  }, [subtitleText]);

  // Render methods
  const renderAudioControls = useMemo(() => {
    if (!audioState.finalAudioUrl) return null;

    return (
      <div className="result">
        <h2>Generated Audio</h2>
        <div className="combined-audio">
          <h3>Combined Audio</h3>
          <AudioControls audioUrl={audioState.finalAudioUrl} />
        </div>
        <div className="srt-controls">
          <button onClick={downloadCombinedSRT} className="btn srt-btn">
            Download Combined SRT
          </button>
        </div>
      </div>
    );
  }, [audioState.finalAudioUrl]);

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
        <input
          type="file"
          id="referenceAudio"
          onChange={handleFileChange}
          accept="audio/wav"
          className="audio-input"
          required
        />
        {error && <div className="error-message">{error}</div>}
        {renderAudioControls}
        <button
          type="submit"
          className="generate-btn"
          disabled={audioState.isProcessing}
        >
          {audioState.isProcessing ? "Generating..." : "Generate Audio"}
        </button>
      </div>
    </div>
  );
};

SubtitleEditor.propTypes = {
  subtitleText: PropTypes.string,
  setIsProcessing: PropTypes.func.isRequired,
};

export default SubtitleEditor;
