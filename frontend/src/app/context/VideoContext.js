import React, { createContext, useState, useContext, useEffect } from 'react';

const VideoContext = createContext();

export const VideoProvider = ({ children }) => {
  const [videos, setVideos] = useState(() => {
    const savedVideos = localStorage.getItem('videos');
    return savedVideos ? JSON.parse(savedVideos) : [];
  });

  // Save to localStorage whenever videos change
  useEffect(() => {
    localStorage.setItem('videos', JSON.stringify(videos));
  }, [videos]);

  const addVideo = (video) => {
    setVideos(prevVideos => {
      // Find the highest ID number
      const maxId = prevVideos.reduce((max, v) => {
        const idNum = parseInt(v.id.replace('VID', ''));
        return idNum > max ? idNum : max;
      }, 0);
      
      // Create new video with incremented ID
      const newVideo = {
        ...video,
        id: `VID${String(maxId + 1).padStart(6, '0')}`,
        createdAt: new Date().toISOString()
      };
      
      return [...prevVideos, newVideo];
    });
  };

  const updateVideo = (id, updates) => {
    setVideos(prevVideos => 
      prevVideos.map(video => 
        video.id === id ? { ...video, ...updates } : video
      )
    );
  };

  const deleteVideo = (id) => {
    setVideos(prevVideos => prevVideos.filter(video => video.id !== id));
  };

  return (
    <VideoContext.Provider value={{ videos, addVideo, updateVideo, deleteVideo }}>
      {children}
    </VideoContext.Provider>
  );
};

export const useVideos = () => {
  const context = useContext(VideoContext);
  if (!context) {
    throw new Error('useVideos must be used within a VideoProvider');
  }
  return context;
};