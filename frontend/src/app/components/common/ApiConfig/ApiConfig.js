import React, { useState, useEffect } from 'react';
import { BASE_URL } from '../../../services/api';

const ApiConfig = () => {
  const [apiUrl, setApiUrl] = useState(() => {
    return localStorage.getItem('api_base_url') || BASE_URL;
  });
  const [isConfigVisible, setIsConfigVisible] = useState(false);
  const [testStatus, setTestStatus] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleSaveUrl = () => {
    localStorage.setItem('api_base_url', apiUrl);
    alert('API URL đã được lưu. Làm mới trang để áp dụng thay đổi.');
    window.location.reload();
  };

  const handleTestConnection = async () => {
    setIsLoading(true);
    setTestStatus(null);
    
    try {
      const response = await fetch(`${apiUrl}/`);
      
      if (response.ok) {
        setTestStatus({ success: true, message: 'Kết nối thành công!' });
      } else {
        setTestStatus({ 
          success: false, 
          message: `Lỗi: ${response.status} ${response.statusText}` 
        });
      }
    } catch (error) {
      setTestStatus({ 
        success: false, 
        message: `Không thể kết nối: ${error.message}` 
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleReset = () => {
    localStorage.removeItem('api_base_url');
    setApiUrl(BASE_URL);
    alert('Đã đặt lại về địa chỉ mặc định.');
    window.location.reload();
  };

  return (
    <div style={{ margin: '20px 0', position: 'relative' }}>
      <button 
        onClick={() => setIsConfigVisible(!isConfigVisible)}
        style={{
          position: 'fixed',
          bottom: '20px',
          right: '20px',
          padding: '10px',
          background: '#007bff',
          color: 'white',
          border: 'none',
          borderRadius: '4px',
          cursor: 'pointer',
          zIndex: 1000
        }}
      >
        ⚙️ Cấu hình API
      </button>
      
      {isConfigVisible && (
        <div style={{
          position: 'fixed',
          bottom: '70px',
          right: '20px',
          width: '350px',
          padding: '15px',
          backgroundColor: 'white',
          boxShadow: '0 0 10px rgba(0,0,0,0.2)',
          borderRadius: '8px',
          zIndex: 1000
        }}>
          <h3>Cấu hình API</h3>
          <div style={{ marginBottom: '10px' }}>
            <label style={{ display: 'block', marginBottom: '5px' }}>
              API URL (ví dụ: http://your-ngrok-url.ngrok.io):
            </label>
            <input 
              type="text" 
              value={apiUrl}
              onChange={(e) => setApiUrl(e.target.value)}
              style={{
                width: '100%',
                padding: '8px',
                border: '1px solid #ccc',
                borderRadius: '4px'
              }}
            />
          </div>
          
          <div style={{ marginBottom: '10px' }}>
            <button 
              onClick={handleTestConnection}
              disabled={isLoading}
              style={{
                padding: '8px 15px',
                backgroundColor: '#28a745',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                marginRight: '10px',
                cursor: isLoading ? 'not-allowed' : 'pointer'
              }}
            >
              {isLoading ? 'Đang kiểm tra...' : 'Kiểm tra kết nối'}
            </button>
            
            <button 
              onClick={handleSaveUrl}
              style={{
                padding: '8px 15px',
                backgroundColor: '#007bff',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer'
              }}
            >
              Lưu
            </button>
            
            <button 
              onClick={handleReset}
              style={{
                padding: '8px 15px',
                backgroundColor: '#dc3545',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                marginLeft: '10px',
                cursor: 'pointer'
              }}
            >
              Reset
            </button>
          </div>
          
          {testStatus && (
            <div style={{
              padding: '10px',
              backgroundColor: testStatus.success ? '#d4edda' : '#f8d7da',
              color: testStatus.success ? '#155724' : '#721c24',
              borderRadius: '4px',
              marginTop: '10px'
            }}>
              {testStatus.message}
            </div>
          )}
          
          <p style={{ fontSize: '12px', color: '#6c757d', marginTop: '10px' }}>
            <strong>Hiện tại:</strong> {localStorage.getItem('api_base_url') || BASE_URL}
          </p>
        </div>
      )}
    </div>
  );
};

export default ApiConfig;