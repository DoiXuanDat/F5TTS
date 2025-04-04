// frontend/src/app/components/subtitle/SubtitleRow.js

import React, { memo, useCallback } from "react";
import PropTypes from "prop-types";
import "./SubtitleRow.css";

const SubtitleRow = memo(({
  subtitle,
  index,
  onUpdateSubtitle,
  onDeleteSubtitle,
  onAddSubtitleUp,
  onAddSubtitleDown,
  onImageClick,
  onSplitSubtitle,
}) => {

  // Handle text changes with support for multiple paragraphs
  const handleTextChange = useCallback((e) => {
    const newText = e.target.value;
    onUpdateSubtitle(subtitle.id, newText);
  }, [subtitle.id, onUpdateSubtitle]);

  // Handle key presses
  const handleKeyDown = useCallback((e) => {
    // Only handle Enter key
    if (e.key === "Enter") {
      if (e.shiftKey) {
        // Allow Shift+Enter for new lines
        return;
      }
      
      // Regular Enter - prevent default and split at cursor
      e.preventDefault();
      const cursorPosition = e.target.selectionStart;
      const text = e.target.value;
      const firstPart = text.substring(0, cursorPosition);
      const secondPart = text.substring(cursorPosition);
      
      // Create new subtitle only on regular Enter
      onSplitSubtitle(subtitle.id, secondPart, index);
      onUpdateSubtitle(subtitle.id, firstPart);
    }
  }, [subtitle.id, index, onSplitSubtitle, onUpdateSubtitle]);

  const handleDelete = useCallback(() => {
    onDeleteSubtitle(subtitle.id);
  }, [subtitle.id, onDeleteSubtitle]);

  const handleImageClick = useCallback(() => {
    onImageClick(subtitle.id);
  }, [subtitle.id, onImageClick]);

  return (
    <tr className="subtitle-row">
      <td className="subtitle-number">{index + 1}</td>
      <td className="subtitle-content">
        <textarea
          rows="4"
          value={subtitle.text}
          onChange={handleTextChange}
          onKeyDown={handleKeyDown}
          placeholder="Enter subtitle text here..."
          className="subtitle-textarea"
          aria-label={`Subtitle ${index + 1}`}
        />
        <div className="subtitle-actions">
          <button
            onClick={() => onAddSubtitleUp(subtitle.id)}
            className="action-btn add-up"
            title="Add subtitle above"
          >
            ➕⬆️
          </button>
          <button
            onClick={() => onAddSubtitleDown(subtitle.id)}
            className="action-btn add-down"
            title="Add subtitle below"
          >
            ➕⬇️
          </button>
          <button
            onClick={handleDelete}
            className="action-btn delete"
            title="Delete subtitle"
          >
            ➖
          </button>
        </div>
      </td>
      <td className="subtitle-image">
        {subtitle.image && (
          <img
            src={subtitle.image}
            alt={`Preview ${index + 1}`}
            className="thumbnail"
            onClick={handleImageClick}
            loading="lazy"
          />
        )}
      </td>
    </tr>
  );
});

SubtitleRow.propTypes = {
  subtitle: PropTypes.shape({
    id: PropTypes.string.isRequired,
    text: PropTypes.string.isRequired,
    image: PropTypes.string,
  }).isRequired,
  index: PropTypes.number.isRequired,
  onUpdateSubtitle: PropTypes.func.isRequired,
  onDeleteSubtitle: PropTypes.func.isRequired,
  onAddSubtitleUp: PropTypes.func.isRequired,
  onAddSubtitleDown: PropTypes.func.isRequired,
  onImageClick: PropTypes.func.isRequired,
  onSplitSubtitle: PropTypes.func.isRequired,
};

SubtitleRow.displayName = "SubtitleRow";

export default SubtitleRow;