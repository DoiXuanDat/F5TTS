import React from "react";
import { BrowserRouter as Router, Route, Routes } from "react-router-dom";
import "./App.css";
import { VideoProvider } from "./context/VideoContext";
import SubtitleVoiceStudio from "./pages/subtitleVoiceStudio/SubtitleVoiceStudio";
import VideoListPage from "./pages/videoList/VideoListPage";
import ImportText from './pages/importText/ImportText';

function App() {
  return (
    <VideoProvider>
      <Router>
        <Routes>
          
          <Route path="/" element={<SubtitleVoiceStudio />} />
          <Route path="/video-list" element={<VideoListPage />} />
          <Route path="/import-text" element={<ImportText />} />
        </Routes>
      </Router>
    </VideoProvider>
  );
}

export default App;
