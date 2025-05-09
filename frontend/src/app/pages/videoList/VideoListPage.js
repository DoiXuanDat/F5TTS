import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { FaCopy, FaEdit, FaPlay, FaTrash, FaPlus } from "react-icons/fa";
import axios from "axios";
import { getBaseURL } from "../../services/api";
import "./VideoListPage.css";


const VideoListPage = () => {
  const [videos, setVideos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  const fetchVideos = async () => {
    try {
      console.log('Fetching videos from:', `${getBaseURL()}/videos/`);
      const response = await axios.get(`${getBaseURL()}/videos/`);
      console.log('Response data:', response.data);
      
      // Kiểm tra dữ liệu
      if (Array.isArray(response.data)) {
        setVideos(response.data);
      } else {
        console.error('Unexpected data format:', response.data);
        setError('Dữ liệu không đúng định dạng');
      }
      
    } catch (err) {
      console.error('Error fetching videos:', err);
      setError(err.message || "Failed to fetch videos");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // Initial fetch
    fetchVideos();

    // Set up polling with longer interval and only for processing videos
    const interval = setInterval(() => {
      // Only poll if there are videos in processing state
      const hasProcessingVideos = videos.some(
        video => video.status === 'pending' || 
                video.status === 'processing' ||
                video.status === 'kokoro-processing'
      );

      if (hasProcessingVideos) {
        fetchVideos();
      }
    }, 5000); // Changed from default to 5 seconds

    return () => clearInterval(interval);
  }, [videos]); // Added videos dependency

  const handleCopyUrl = (url) => {
    navigator.clipboard.writeText(url);
    // Add toast notification here if desired
  };

  const renderTtsProvider = (video) => {
    if (!video.metadata || !video.metadata.source) {
      // Check audio path to determine provider
      if (video.audio_path?.includes('kokoro')) {
        return "Kokoro-TTS";
      }
      return "F5-TTS";
    }
    
    const sourceMap = {
      "f5-tts": "F5-TTS",
      "minimax": "MiniMax.io",
      "kokoro": "Kokoro-TTS"
    };
    
    return sourceMap[video.metadata.source] || "Unknown";
  };

  const handleDelete = async (id) => {
    if (window.confirm("Bạn có chắc chắn muốn xóa video này?")) {
      try {
        await axios.delete(`${getBaseURL()}/videos/${id}`);
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
      error: `Lỗi: ${error || 'Không xác định'}`,
      'kokoro-processing': "Đang tạo âm thanh (Kokoro)",
      'kokoro-error': `Lỗi Kokoro TTS: ${error || 'Không xác định'}`
    };
    return statusMap[status] || status;
  };

  const getStatusClass = (status) => {
    if (status?.includes('kokoro')) {
      return `status-badge kokoro-${status.split('-')[1]}`;
    }
    return `status-badge ${status}`;
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
                <th>TTS Provider</th>
                <th>Trạng Thái</th>
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
                                navigator.clipboard.writeText(`${getBaseURL()}/${video.url}`);
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
                            onClick={() => window.open(`${getBaseURL()}/${video.url}`, "_blank")}
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
                  <td className="tts-provider-cell">
                    <span className={`tts-provider-badge ${video.metadata?.source || "f5-tts"}`}>
                      {renderTtsProvider(video)}
                    </span>
                  </td>
                  <td>
                    <span className={getStatusClass(video.status)}>
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