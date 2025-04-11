import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { BASE_URL } from '../../../services/api';

const ApiConfig = () => {
  // Get initial URL from localStorage or use the default
  const [apiUrl, setApiUrl] = useState(() => {
    return localStorage.getItem('api_base_url') || BASE_URL;
  });
  
  const [isConfigVisible, setIsConfigVisible] = useState(false);
  const [testStatus, setTestStatus] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isAutoDetecting, setIsAutoDetecting] = useState(false);
  
  // Try to auto-detect the server's ngrok URL when the component mounts
  useEffect(() => {
    const currentUrl = window.location.origin;
    
    // Kiểm tra nếu URL hiện tại là ngrok URL
    if (currentUrl.includes('ngrok') && !localStorage.getItem('api_base_url')) {
      // Tự động cập nhật ngrok URL
      localStorage.setItem('api_base_url', currentUrl);
      setApiUrl(currentUrl);
      
      // Thông báo cho người dùng
      setTestStatus({
        success: true,
        message: 'Đã tự động cập nhật URL API từ ngrok'
      });
    }
  }, []);
  
  const handleSaveUrl = () => {
    localStorage.setItem('api_base_url', apiUrl);
    alert('API URL has been saved. Refreshing page to apply changes.');
    window.location.reload();
  };
  
  const testConnection = async (urlToTest = apiUrl) => {
    setIsLoading(true);
    setTestStatus(null);
    
    try {
      // First try a basic connection test
      const response = await axios.get(`${urlToTest}/`, { timeout: 5000 });
      
      if (response.status >= 200 && response.status < 300) {
        setTestStatus({ 
          success: true, 
          message: 'Connection successful! Server is responding.' 
        });
        return true;
      } else {
        setTestStatus({ 
          success: false, 
          message: `Error: ${response.status} ${response.statusText}` 
        });
        return false;
      }
    } catch (error) {
      console.error('Connection test error:', error);
      setTestStatus({ 
        success: false, 
        message: `Cannot connect: ${error.message}` 
      });
      return false;
    } finally {
      setIsLoading(false);
    }
  };
  
  const handleTestConnection = () => testConnection();
  
  const handleReset = () => {
    localStorage.removeItem('api_base_url');
    localStorage.removeItem('has_auto_detected');
    setApiUrl(BASE_URL);
    alert('Reset to default address.');
    window.location.reload();
  };
  
  const handleAutoDetect = async () => {
    if (window.location.href.includes('ngrok')) {
      const currentOrigin = window.location.origin;
      setApiUrl(currentOrigin);
      await testConnection(currentOrigin);
    } else {
      setTestStatus({
        success: false,
        message: 'Cannot auto-detect: This page is not served through ngrok.'
      });
    }
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
        ⚙️ API Config
      </button>
      
      {isConfigVisible && (
        <div style={{
          position: 'fixed',
          bottom: '70px',
          right: '20px',
          width: '380px',
          padding: '15px',
          backgroundColor: 'white',
          boxShadow: '0 0 10px rgba(0,0,0,0.2)',
          borderRadius: '8px',
          zIndex: 1000
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
            <h3 style={{ margin: 0 }}>API Configuration</h3>
            <button 
              onClick={() => setIsConfigVisible(false)}
              style={{
                background: 'none',
                border: 'none',
                fontSize: '16px',
                cursor: 'pointer'
              }}
            >
              ✕
            </button>
          </div>
          
          {isAutoDetecting && (
            <div style={{
              padding: '10px',
              backgroundColor: '#cff4fc',
              color: '#055160',
              borderRadius: '4px',
              marginBottom: '10px'
            }}>
              Auto-detecting server configuration...
            </div>
          )}
          
          <div style={{ marginBottom: '15px' }}>
            <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>
              API URL (example: https://your-ngrok-url.ngrok.io):
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
            <div style={{ fontSize: '12px', color: '#6c757d', marginTop: '5px' }}>
              * This must be the full URL, including https://
            </div>
          </div>
          
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginBottom: '15px' }}>
            <button 
              onClick={handleAutoDetect}
              style={{
                padding: '8px 15px',
                backgroundColor: '#6610f2',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer'
              }}
            >
              Auto-Detect
            </button>
            
            <button 
              onClick={handleTestConnection}
              disabled={isLoading}
              style={{
                padding: '8px 15px',
                backgroundColor: '#28a745',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: isLoading ? 'not-allowed' : 'pointer',
                opacity: isLoading ? 0.7 : 1
              }}
            >
              {isLoading ? 'Testing...' : 'Test Connection'}
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
              Save
            </button>
            
            <button 
              onClick={handleReset}
              style={{
                padding: '8px 15px',
                backgroundColor: '#dc3545',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
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
          
          <div style={{ 
            fontSize: '12px', 
            color: '#6c757d', 
            marginTop: '15px',
            padding: '10px',
            backgroundColor: '#f8f9fa',
            borderRadius: '4px'
          }}>
            <strong>Current API URL:</strong> {localStorage.getItem('api_base_url') || BASE_URL}
            <br/>
            <br/>
            <strong>How this works:</strong>
            <ol style={{ margin: '5px 0 0 20px', padding: 0 }}>
              <li>When someone shares the app, they share their ngrok URL</li>
              <li>You enter this URL here and click "Test Connection"</li>
              <li>After saving, the app will use their server instead of your localhost</li>
            </ol>
          </div>
        </div>
      )}
    </div>
  );
};

export default ApiConfig;