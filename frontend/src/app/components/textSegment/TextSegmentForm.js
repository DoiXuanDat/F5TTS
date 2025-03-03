import React from "react";
import PropTypes from "prop-types";

const TextSegmentForm = ({
  segments,
  refText,
  showTiming,
  onRefTextChange,
  onSegmentChange,
  onRemoveSegment,
  onAddSegment,
  onShowTimingToggle,
  onSubmit,
}) => {
  return (
    <form onSubmit={onSubmit}>
      <div className="form-group">
        <label htmlFor="ref_text">Reference Text:</label>
        <input
          type="text"
          id="ref_text"
          value={refText}
          onChange={(e) => onRefTextChange(e.target.value)}
          required
          placeholder="Enter reference text"
        />
      </div>

      <div className="timing-controls">
        <button type="button" onClick={onShowTimingToggle} className="btn">
          {showTiming ? "Hide Timing Info" : "Show Timing Info"}
        </button>
      </div>

      {segments.map((segment, index) => (
        <div key={index} className="segment-group">
          <div className="segment-header">
            <h3>Text Segment {index + 1}</h3>
            {segments.length > 1 && (
              <button
                type="button"
                className="btn remove-segment"
                onClick={() => onRemoveSegment(index)}
              >
                Remove
              </button>
            )}
          </div>
          <textarea
            className="gen-text-segment"
            value={segment.text}
            onChange={(e) => onSegmentChange(index, e.target.value)}
            required
            placeholder="Enter text to generate"
          />
          {showTiming && (
            <div className="timing-info">
              <span className="duration">
                Duration: {segment.duration || "--"}
              </span>
            </div>
          )}
        </div>
      ))}

      <button
        type="button"
        className="btn add-segment-btn"
        onClick={onAddSegment}
      >
        Add Another Segment
      </button>
    </form>
  );
};

TextSegmentForm.propTypes = {
  segments: PropTypes.arrayOf(
    PropTypes.shape({
      text: PropTypes.string,
      duration: PropTypes.number,
    })
  ).isRequired,
  refText: PropTypes.string.isRequired,
  showTiming: PropTypes.bool.isRequired,
  onRefTextChange: PropTypes.func.isRequired,
  onSegmentChange: PropTypes.func.isRequired,
  onRemoveSegment: PropTypes.func.isRequired,
  onAddSegment: PropTypes.func.isRequired,
  onShowTimingToggle: PropTypes.func.isRequired,
  onSubmit: PropTypes.func.isRequired,
};

export default TextSegmentForm;
