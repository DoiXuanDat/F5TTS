import React, { useState, useEffect } from "react";
import FilePicker from "../common/filePicker/FilePicker";
import SubtitleList from "./SubtitleList";
import Settings from "../common/settings/Settings";
import "./SubtitleEditor.css";

const SubtitleEditor = ({ subtitleText }) => {
  const [subtitles, setSubtitles] = useState([]);
  const [imageList, setImageList] = useState([
    require("../../assets/images/30.png"),
    require("../../assets/images/31.png"),
    require("../../assets/images/32.png"),
    require("../../assets/images/33.png"),
  ]);
  const [selectedId, setSelectedId] = useState(null);
  const [isPickerOpen, setPickerOpen] = useState(false);
  const [noTextTime, setNoTextTime] = useState(0);
  const [sentencePause, setSentencePause] = useState(0);
  const [paragraphPause, setParagraphPause] = useState(0);
  const [splitBy, setSplitBy] = useState("° .");
  const [dllitems, setDllitems] = useState("⌊ ⌉");

  useEffect(() => {
    if (subtitleText) {
      const paragraphs = subtitleText
        .split("\n\n")
        .filter((p) => p.trim() !== "");
      const newSubtitles = paragraphs.map((paragraph, index) => ({
        id: `${Date.now()}-${index}`,
        text: paragraph.trim(),
        image: imageList[index % imageList.length],
      }));

      setSubtitles(newSubtitles);
    }
  }, [subtitleText, imageList]);

  const handleImageClick = (id) => {
    setSelectedId(id);
    setPickerOpen(true);
  };

  const handleSelectImage = (image) => {
    setSubtitles((prevData) =>
      prevData.map((item) =>
        item.id === selectedId ? { ...item, image } : item
      )
    );
    setPickerOpen(false);
  };

  const updateImageList = (newImage) => {
    setImageList((prevList) => [...prevList, newImage]);
  };

  const updateSubtitle = (id, newText) => {
    setSubtitles((prevSubtitles) =>
      prevSubtitles.map((subtitle) =>
        subtitle.id === id ? { ...subtitle, text: newText } : subtitle
      )
    );
  };

  const addSubtitleDown = () => {
    setSubtitles((prevSubtitles) => [
      ...prevSubtitles,
      { id: `${Date.now()}-new`, text: "", image: imageList[0] },
    ]);
  };

  const addSubtitleUp = () => {
    setSubtitles((prevSubtitles) => [
      { id: `${Date.now()}-new`, text: "", image: imageList[0] },
      ...prevSubtitles,
    ]);
  };

  const deleteSubtitle = (id) => {
    setSubtitles((prevSubtitles) =>
      prevSubtitles.filter((subtitle) => subtitle.id !== id)
    );
  };
  const splitSubtitle = (id, newText, index) => {
    setSubtitles((prevSubtitles) => {
      const currentSubtitle = prevSubtitles.find((s) => s.id === id);
      const imageToUse = currentSubtitle ? currentSubtitle.image : imageList[0];
      const newSubtitle = {
        id: `${Date.now()}-split`,
        text: newText,
        image: imageToUse,
      };
      const updatedSubtitles = [...prevSubtitles];
      updatedSubtitles.splice(index, 0, newSubtitle);
      return updatedSubtitles;
    });
  };

  const splitSentences = () => {
    setSubtitles((prevSubtitles) => {
      let allSubtitles = [];

      prevSubtitles.forEach((subtitle) => {
        const splitPattern = new RegExp(`[${splitBy}]\\s*`, "g");
        const sentences = subtitle.text
          .split(splitPattern)
          .filter((sentence) => sentence.trim() !== "")
          .map((sentence) => sentence.trim());

        if (sentences.length > 1) {
          const newSubtitles = sentences.map((sentence, idx) => ({
            id: `${Date.now()}-${subtitle.id}-${idx}`,
            text: sentence,
            image: subtitle.image,
          }));

          allSubtitles = [...allSubtitles, ...newSubtitles];
        } else {
          allSubtitles.push(subtitle);
        }
      });

      return allSubtitles;
    });
  };

  const deleteSpecialCharacter = () => {
    setSubtitles((prevSubtitles) =>
      prevSubtitles.map((subtitle) => ({
        ...subtitle,
        text: subtitle.text.replace(
          new RegExp(`[${dllitems.replace(/\s/g, "")}]`, "g"),
          ""
        ),
      }))
    );
  };

  return (
    <div className="subtitle-editor">
      <Settings
        noTextTime={noTextTime}
        setNoTextTime={setNoTextTime}
        sentencePause={sentencePause}
        setSentencePause={setSentencePause}
        paragraphPause={paragraphPause}
        setParagraphPause={setParagraphPause}
        splitBy={splitBy}
        setSplitBy={setSplitBy}
        dllitems={dllitems}
        setDllitems={setDllitems}
        splitSentences={splitSentences}
        deleteSpecialCharacter={deleteSpecialCharacter}
      />
      <SubtitleList
        subtitles={subtitles}
        onUpdateSubtitle={updateSubtitle}
        onDeleteSubtitle={deleteSubtitle}
        onAddSubtitleUp={addSubtitleUp}
        onAddSubtitleDown={addSubtitleDown}
        onImageClick={handleImageClick}
        onSplitSubtitle={splitSubtitle}
      />
      {isPickerOpen && (
        <FilePicker
          onClose={() => setPickerOpen(false)}
          onSelect={handleSelectImage}
          imageList={imageList}
          updateImageList={updateImageList}
        />
      )}
    </div>
  );
};

export default SubtitleEditor;
