import React from "react";

const FilePicker = ({ onClose, onSelect, imageList, updateImageList }) => {
  const handleFileChange = (event) => {
    if (event.target.files.length > 0) {
      const file = event.target.files[0];
      const reader = new FileReader();
      reader.onloadend = () => {
        const newImage = reader.result;
        updateImageList(newImage);
        onSelect(newImage);
      };
      reader.readAsDataURL(file);
    }
  };

  const getFileName = (imgPath) => {
    const fileName = imgPath.split("/").pop();
    return fileName.split(".")[0] + ".png";
  };

  return (
    <div className="modal">
      <div className="modal-dialog">
        <div className="modal-content">
          <div className="modal-header">
            <h2>Chọn file</h2>
            <button type="button" className="btn-close" onClick={onClose}></button>
          </div>
          <div className="modal-body">
            <div className="image-grid">
              <div className="add-image">
                <input
                  type="file"
                  id="fileInput"
                  style={{ display: "none" }}
                  onChange={handleFileChange}
                />
                <label htmlFor="fileInput" className="add-file-content">
                  <i className="bi bi-plus-square-fill"></i>
                </label>
              </div>
              {imageList.map((img, index) => (
                <div key={index} className="image-box" onClick={() => onSelect(img)}>
                  <img src={img} alt={img} />
                  <p>{getFileName(img)}</p>
                </div>
              ))}
            </div>
          </div>
          <div className="modal-footer">
            <div className="actionns">
              <button className="btn btn-success">Tích tất cả</button>
              <button className="btn btn-danger">Bỏ tích</button>
              <button className="btn btn-primary">Chọn</button>
              <button className="btn btn-light" onClick={onClose}>Hủy</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default FilePicker;