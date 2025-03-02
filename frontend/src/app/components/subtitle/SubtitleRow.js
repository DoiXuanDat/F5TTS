import React from "react";

const SubtitleRow = ({
  subtitle,
  index,
  onUpdateSubtitle,
  onDeleteSubtitle,
  onAddSubtitleUp,
  onAddSubtitleDown,
  onImageClick,
  onSplitSubtitle,
}) => {
  const handleTextChange = (e) => {
    const newText = e.target.value;
    onUpdateSubtitle(subtitle.id, newText);
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      const cursorPosition = e.target.selectionStart;
      const text = e.target.value;
      const firstPart = text.substring(0, cursorPosition).trim();
      const secondPart = text.substring(cursorPosition).trim();
      onSplitSubtitle(subtitle.id, secondPart, index + 1);
      onUpdateSubtitle(subtitle.id, firstPart);
    }
  };

  return (
    <tr className="row">
      <td className="col-1">{index + 1}</td>
      <td className="col-7">
        <textarea
          rows="4"
          value={subtitle.text}
          onChange={handleTextChange}
          onKeyDown={handleKeyDown}
          placeholder="Enter subtitle text here..."
        />
        <div className="actions">
          <button onClick={onAddSubtitleUp}>➕⬆️</button>
          <button onClick={onAddSubtitleDown}>➕⬇️</button>
          <button onClick={() => onDeleteSubtitle(subtitle.id)}>➖</button>
        </div>
      </td>
      <td className="col-4">
        <img
          src={subtitle.image}
          alt="Preview"
          className="thumbnail"
          onClick={() => onImageClick(subtitle.id)}
        />
      </td>
    </tr>
  );
};

export default SubtitleRow;
