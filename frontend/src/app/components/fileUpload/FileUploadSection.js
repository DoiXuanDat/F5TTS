import React from "react";
import PropTypes from "prop-types";

const FileUploadSection = ({
  regexPath,
  dllitems,
  onRegexChange,
  onDllitemsChange,
  onSplitText,
  onDeleteSpecialChars,
  onFileUpload,
}) => {
  return (
    <div className="file-upload-section">
      <div className="formRegex">
        <label>Regex chia dòng:</label>
        <input
          type="text"
          className="regexInput"
          placeholder="Enter regex"
          value={regexPath}
          onChange={(e) => onRegexChange(e.target.value)}
        />
        <button className="button btn btn-primary" onClick={onSplitText}>
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
          onChange={(e) => onDllitemsChange(e.target.value)}
        />
        <button className="button btn btn-danger" onClick={onDeleteSpecialChars}>
          Xóa
        </button>
      </div>
      <input
        className="mt-1"
        type="file"
        accept=".srt,.ass"
        onChange={onFileUpload}
        id="file-upload"
        style={{ display: "none" }}
      />
      <label htmlFor="file-upload" className="button btn btn-info">
        Chọn file (.srt, .ass)
      </label>
    </div>
  );
};

FileUploadSection.propTypes = {
  regexPath: PropTypes.string.isRequired,
  dllitems: PropTypes.string.isRequired,
  onRegexChange: PropTypes.func.isRequired,
  onDllitemsChange: PropTypes.func.isRequired,
  onSplitText: PropTypes.func.isRequired,
  onDeleteSpecialChars: PropTypes.func.isRequired,
  onFileUpload: PropTypes.func.isRequired,
};

export default FileUploadSection;