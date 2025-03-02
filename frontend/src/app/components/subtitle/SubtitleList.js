import React from "react";
import SubtitleRow from "./SubtitleRow";

const SubtitleList = ({
  subtitles,
  onUpdateSubtitle,
  onDeleteSubtitle,
  onAddSubtitleUp,
  onAddSubtitleDown,
  onImageClick,
  onSplitSubtitle,
}) => {
  return (
    <div className="subtitle-table">
      <table>
        <thead>
          <tr className="row">
            <th className="col-1">STT</th>
            <th className="col-7">Text</th>
            <th className="col-4">Hình ảnh/Video</th>
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
};

export default SubtitleList;
