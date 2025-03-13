import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { FaCopy, FaEdit, FaPlay, FaTrash, FaPlus } from "react-icons/fa";
import axios from "axios";
import { BASE_URL } from "../../services/api";
import "./VideoListPage.css";

const VideoListPage = () => {
  const [videos, setVideos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  const fetchVideos = async () => {
    try {
      const response = await axios.get(`${BASE_URL}/videos/`);
      if (Array.isArray(response.data)) {
        setVideos(response.data);
      } else {
        setVideos([]);
      }
      setLoading(false);
    } catch (err) {
      setError(err.message || "Failed to fetch videos");
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchVideos();
    const interval = setInterval(fetchVideos, 30000); 
    return () => clearInterval(interval);
  }, []);

  const handleCopyUrl = (url) => {
    navigator.clipboard.writeText(url);
    // Add toast notification here if desired
  };

  const handleDelete = async (id) => {
    if (window.confirm("Bạn có chắc chắn muốn xóa video này?")) {
      try {
        await axios.delete(`${BASE_URL}/videos/${id}`);
        setVideos(videos.filter(video => video.id !== id));
      } catch (err) {
        console.error("Error deleting video:", err);
      }
    }
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleString("vi-VN", {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const renderStatus = (status, error) => {
    const statusMap = {
      completed: "Hoàn thành",
      processing: "Đang xử lý",
      pending: "Đang chờ",
      error: `Lỗi: ${error || 'Không xác định'}`
    };
    return statusMap[status] || status;
  };

  return (
    <div className="video-list-container">
      <div className="video-list-header">
        <h1>Danh sách video ({videos.length})</h1>
        <div className="header-buttons">
          <button 
            className="btn btn-primary" 
            onClick={() => navigate("/")}
          >
            <FaPlus className="me-2" />
            Tạo video mới
          </button>
        </div>
      </div>

      {loading && <div className="alert alert-info">Đang tải dữ liệu...</div>}
      {error && <div className="alert alert-danger">Lỗi: {error}</div>}
      
      {!loading && !error && videos.length === 0 && (
        <div className="alert alert-warning">Chưa có video nào</div>
      )}

      {!loading && !error && videos.length > 0 && (
        <div className="video-list-content">
          <table className="table">
            <thead>
              <tr>
                <th>Video</th>
                <th>Trạng thái</th>
                <th>ID</th>
                <th>Ngày tạo</th>
              </tr>
            </thead>
            <tbody>
              {videos.map((video) => (
                <tr key={video.id}>
                  <td className="video-cell">
                    <div className="video-info">
                      <img
                        src={video.thumbnail || '/default-thumbnail.png'}
                        alt={video.title}
                        className="video-thumbnail"
                      />
                      <div className="video-details">
                        <h3>{video.title}</h3>
                        <div className="video-actions">
                          <button
                            className="action-btn"
                            onClick={() => {
                              if (video.url) {
                                navigator.clipboard.writeText(`${BASE_URL}/${video.url}`);
                                alert('Đã sao chép đường dẫn!');
                              }
                            }}
                            disabled={!video.url}
                            title="Sao chép đường dẫn"
                          >
                            <FaCopy />
                          </button>
                          <button
                            className="action-btn"
                            onClick={() => navigate(`/subtitle-editor/${video.id}`)}
                            title="Chỉnh sửa"
                            disabled={video.status === 'processing'}
                          >
                            <FaEdit />
                          </button>
                          <button
                            className="action-btn"
                            onClick={() => window.open(`${BASE_URL}/${video.url}`, "_blank")}
                            disabled={!video.url || video.status !== 'completed'}
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
                      {renderStatus(video.status, video.error)}
                    </span>
                  </td>
                  <td>{video.id}</td>
                  <td>{formatDate(video.createdAt)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default VideoListPage;
