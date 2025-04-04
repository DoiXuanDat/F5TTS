import React, { memo } from "react";
import PropTypes from "prop-types";
import SubtitleRow from "./SubtitleRow";
import "./SubtitleList.css";

const SubtitleList = memo(
  ({
    subtitles,
    onUpdateSubtitle,
    onDeleteSubtitle,
    onAddSubtitleUp,
    onAddSubtitleDown,
    onImageClick,
    onSplitSubtitle,
  }) => {
    return (
      <div className="subtitle-table-container">
        <table className="subtitle-table">
          <thead>
            <tr>
              <th>No.</th>
              <th>Text</th>
              <th>Image/Video</th>
            </tr>
          </thead>
          <tbody>
            {subtitles.map((subtitle, index) => (
              <SubtitleRow
                key={subtitle.id}
                subtitle={subtitle}
                index={index}
                onUpdateSubtitle={onUpdateSubtitle}
                onDeleteSubtitle={onDeleteSubtitle}
                onAddSubtitleUp={onAddSubtitleUp}
                onAddSubtitleDown={onAddSubtitleDown}
                onImageClick={onImageClick}
                onSplitSubtitle={onSplitSubtitle}
              />
            ))}
          </tbody>
        </table>
      </div>
    );
  }
);

SubtitleList.propTypes = {
  subtitles: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.string.isRequired,
      text: PropTypes.string.isRequired,
      image: PropTypes.string,
    })
  ).isRequired,
  onUpdateSubtitle: PropTypes.func.isRequired,
  onDeleteSubtitle: PropTypes.func.isRequired,
  onAddSubtitleUp: PropTypes.func.isRequired,
  onAddSubtitleDown: PropTypes.func.isRequired,
  onImageClick: PropTypes.func.isRequired,
  onSplitSubtitle: PropTypes.func.isRequired,
};

SubtitleList.displayName = "SubtitleList";

export default SubtitleList;