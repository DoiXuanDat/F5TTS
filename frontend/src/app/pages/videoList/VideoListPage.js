import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { FaCopy, FaEdit, FaPlay, FaTrash } from "react-icons/fa";
import "./VideoListPage.css";

const VideoListPage = () => {
  const [videos, setVideos] = useState([
    {
      id: "VID001",
      thumbnail: "/path/to/thumbnail.jpg",
      title: "Video Title 1",
      status: "completed",
      createdAt: "2024-03-03",
      url: "http://example.com/video1",
    },
  ]);

  const navigate = useNavigate();

  const handleCopyUrl = (url) => {
    navigator.clipboard.writeText(url);
    // Optional: Add toast notification
  };

  const handleDelete = (id) => {
    if (window.confirm("Bạn có chắc chắn muốn xóa video này?")) {
      setVideos(videos.filter((video) => video.id !== id));
    }
  };

  return (
    <div className="video-list-container">
      <div className="video-list-header">
        <h1>Danh sách video</h1>
        <button className="btn btn-primary" onClick={() => navigate("/")}>
          Tạo video mới
        </button>
      </div>

      <div className="video-list-content">
        <table className="video-table">
          <thead>
            <tr>
              <th>Video</th>
              <th>Trạng thái</th>
              <th>ID</th>
              <th>Ngày render/tạo</th>
            </tr>
          </thead>
          <tbody>
            {videos.map((video) => (
              <tr key={video.id}>
                <td className="video-cell">
                  <div className="video-info">
                    <img
                      src={video.thumbnail}
                      alt={video.title}
                      className="video-thumbnail"
                    />
                    <div className="video-details">
                      <h3>{video.title}</h3>
                      <div className="video-actions">
                        <button
                          className="action-btn"
                          onClick={() => handleCopyUrl(video.url)}
                          title="Sao chép đường dẫn"
                        >
                          <FaCopy />
                        </button>
                        <button
                          className="action-btn"
                          onClick={() =>
                            navigate(`/subtitle-editor/${video.id}`)
                          }
                          title="Chỉnh sửa"
                        >
                          <FaEdit />
                        </button>
                        <button
                          className="action-btn"
                          onClick={() => window.open(video.url, "_blank")}
                          title="Phát"
                        >
                          <FaPlay />
                        </button>
                        <button
                          className="action-btn delete"
                          onClick={() => handleDelete(video.id)}
                          title="Xóa"
                        >
                          <FaTrash />
                        </button>
                      </div>
                    </div>
                  </div>
                </td>
                <td>
                  <span className={`status-badge ${video.status}`}>
                    {video.status === "completed" ? "Hoàn thành" : "Đang xử lý"}
                  </span>
                </td>
                <td>{video.id}</td>
                <td>{new Date(video.createdAt).toLocaleDateString("vi-VN")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default VideoListPage;
